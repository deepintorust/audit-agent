from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import aio_pika

from src.common.errors import FatalError, RetryableError
from src.mq.messages import FileEvent

logger = logging.getLogger(__name__)


Handler = Callable[[FileEvent], Awaitable[None]]


class Consumer:
    def __init__(self, connection: aio_pika.RobustConnection, queue_name: str, handler: Handler):
        self.connection = connection
        self.queue_name = queue_name
        self.handler = handler
        self._channel: aio_pika.Channel | None = None

    async def run(self) -> None:
        channel = await self.connection.channel()
        self._channel = channel
        await channel.set_qos(prefetch_count=4)
        queue = await channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": f"{self.queue_name}.dlx"},
        )
        async with queue.iterator() as it:
            async for msg in it:
                async with msg.process(ignore_processed=True):
                    event = FileEvent(**json.loads(msg.body.decode("utf-8")))
                    try:
                        await self.handler(event)
                    except RetryableError as e:
                        logger.warning("retryable error: %s", e)
                        await self._retry(msg, event)
                        continue
                    except FatalError as e:
                        logger.error("fatal error: %s", e)
                        await msg.reject(requeue=False)
                        continue
                    except Exception as e:  # noqa: BLE001
                        logger.exception("unexpected error: %s", e)
                        await self._retry(msg, event)

    async def _retry(self, msg: aio_pika.IncomingMessage, event: FileEvent) -> None:
        # Route message to a TTL retry queue based on attempt count.
        # Attempt is persisted in message body; DB step attempt should also be updated by worker.
        attempt = int(event.attempt or 0) + 1
        event.attempt = attempt
        channel = self._channel
        if channel is None:
            raise RuntimeError("consumer channel is not ready")
        body = json.dumps(event.model_dump()).encode("utf-8")
        retry_queue = f"{self.queue_name}.retry.60s" if attempt <= 2 else f"{self.queue_name}.retry.600s"
        await channel.default_exchange.publish(
            aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=retry_queue,
        )
        await msg.ack()
        await asyncio.sleep(0)
