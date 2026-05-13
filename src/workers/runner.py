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

    async def connect_with_backoff(url: str):
        max_retries = int(os.environ.get("RABBITMQ_RETRY_MAX", "12"))
        base = float(os.environ.get("RABBITMQ_RETRY_BASE_SECONDS", "1"))
        attempt = 0
        while True:
            try:
                # Force DNS resolution before each attempt to catch resolution failures early
                loop = asyncio.get_event_loop()
                try:
                    logger.debug("DNS resolution for %s:%s", s.rabbitmq_host, s.rabbitmq_port)
                    addrinfo = await loop.getaddrinfo(
                        s.rabbitmq_host,
                        int(s.rabbitmq_port),
                        family=0,  # Any address family (IPv4/IPv6)
                    )
                    logger.debug("DNS resolved to: %s", addrinfo[0][4][0])
                except Exception as e:
                    logger.error(
                        "DNS resolution failed for %s:%s: %s",
                        s.rabbitmq_host,
                        s.rabbitmq_port,
                        e,
                    )
                    # Fail fast - if we can't resolve the hostname, there's no point retrying
                    raise

                conn = await aio_pika.connect_robust(url)
                return conn
            except Exception as e:
                attempt += 1
                if attempt >= max_retries:
                    logger.exception("AMQP connect failed after %d attempts", attempt)
                    raise
                backoff = base * (2 ** (attempt - 1))
                backoff = min(backoff, 60)
                logger.warning(
                    "AMQP connect attempt %d failed: %s; retrying in %.1fs",
                    attempt,
                    e,
                    backoff,
                )
                await asyncio.sleep(backoff)

    conn = await connect_with_backoff(url)
    handler = get_handler_for_queue(queue)
    consumer = Consumer(conn, queue, handler)
    logger.info("worker started queue=%s", queue)
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(main())
