from __future__ import annotations

import asyncio
import random

from .config import RetryConfig
from .exceptions import RetryExhaustedError, TransportError


RETRYABLE_EXCEPTIONS = (TransportError,)


async def run_with_retry(func, retry_cfg: RetryConfig, *args, **kwargs):
    last_exc = None

    for attempt in range(retry_cfg.max_retries):
        try:
            return await func(*args, **kwargs)

        except RETRYABLE_EXCEPTIONS as exc:
            last_exc = exc

            if attempt >= retry_cfg.max_retries - 1:
                break

            delay = min(
                retry_cfg.base_delay * (2**attempt),
                retry_cfg.max_delay,
            )
            jitter = random.uniform(0, retry_cfg.jitter)

            await asyncio.sleep(delay + jitter)

        except Exception:
            raise

    raise RetryExhaustedError(str(last_exc)) from last_exc
