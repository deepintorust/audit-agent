from __future__ import annotations

import json

import aio_pika

from src.app.settings import Settings
from src.mq.topology import (
    EXCHANGE,
    QUEUE_CHUNK,
    QUEUE_EMBED,
    QUEUE_EXTRACT,
    QUEUE_FUSE,
    QUEUE_INDEX,
    QUEUE_PARSE,
    QUEUE_STORE,
    ROUTING_CHUNK,
    ROUTING_EMBED,
    ROUTING_EXTRACT,
    ROUTING_FUSE,
    ROUTING_INDEX,
    ROUTING_PARSE,
    ROUTING_STORE,
)


class Rabbit:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._conn: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None

    async def connect(self) -> None:
        if self._conn and not self._conn.is_closed:
            return
        url = (
            f"amqp://{self.settings.rabbitmq_user}:{self.settings.rabbitmq_password}"
            f"@{self.settings.rabbitmq_host}:{self.settings.rabbitmq_port}{self.settings.rabbitmq_vhost}"
        )
        self._conn = await aio_pika.connect_robust(url)
        self._channel = await self._conn.channel(publisher_confirms=False)
        await self._declare_topology()

    async def _declare_topology(self) -> None:
        assert self._channel is not None
        ex = await self._channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)

        await self._declare_step_queue(ex, QUEUE_STORE, ROUTING_STORE)
        await self._declare_step_queue(ex, QUEUE_PARSE, ROUTING_PARSE)
        await self._declare_step_queue(ex, QUEUE_EXTRACT, ROUTING_EXTRACT)
        await self._declare_step_queue(ex, QUEUE_FUSE, ROUTING_FUSE)
        await self._declare_step_queue(ex, QUEUE_CHUNK, ROUTING_CHUNK)
        await self._declare_step_queue(ex, QUEUE_EMBED, ROUTING_EMBED)
        await self._declare_step_queue(ex, QUEUE_INDEX, ROUTING_INDEX)

    async def _declare_step_queue(self, ex: aio_pika.Exchange, queue_name: str, routing_key: str) -> None:
        assert self._channel is not None

        dlx_name = f"{queue_name}.dlx"
        dlq_name = f"{queue_name}.dlq"
        dlx = await self._channel.declare_exchange(dlx_name, aio_pika.ExchangeType.FANOUT, durable=True)
        dlq = await self._channel.declare_queue(dlq_name, durable=True)
        await dlq.bind(dlx)

        # Simple retry via TTL queues: 60s and 10m. You can add more tiers.
        retry_60 = await self._channel.declare_queue(
            f"{queue_name}.retry.60s",
            durable=True,
            arguments={
                "x-message-ttl": 60_000,
                "x-dead-letter-exchange": EXCHANGE,
                "x-dead-letter-routing-key": routing_key,
            },
        )
        retry_600 = await self._channel.declare_queue(
            f"{queue_name}.retry.600s",
            durable=True,
            arguments={
                "x-message-ttl": 600_000,
                "x-dead-letter-exchange": EXCHANGE,
                "x-dead-letter-routing-key": routing_key,
            },
        )
        _ = retry_60, retry_600  # declarations only

        q = await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": dlx_name},
        )
        await q.bind(ex, routing_key=routing_key)

    async def publish(self, routing_key: str, event) -> None:
        await self.connect()
        assert self._channel is not None
        ex = await self._channel.get_exchange(EXCHANGE)
        body = json.dumps(event.model_dump()).encode("utf-8")
        msg = aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await ex.publish(msg, routing_key=routing_key)
