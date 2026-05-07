from __future__ import annotations

import asyncio
import logging
import os

import aio_pika

from src.app.logging import configure_logging
from src.app.settings import get_settings
from src.mq.consumer import Consumer
from src.workers.steps import get_handler_for_queue

logger = logging.getLogger(__name__)


async def main() -> None:
    s = get_settings()
    configure_logging(s.app_log_level)
    queue = os.environ.get("WORKER_QUEUE")
    if not queue:
        raise SystemExit("WORKER_QUEUE is required")

    url = (
        f"amqp://{s.rabbitmq_user}:{s.rabbitmq_password}"
        f"@{s.rabbitmq_host}:{s.rabbitmq_port}{s.rabbitmq_vhost}"
    )
    conn = await aio_pika.connect_robust(url)
    handler = get_handler_for_queue(queue)
    consumer = Consumer(conn, queue, handler)
    logger.info("worker started queue=%s", queue)
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(main())

