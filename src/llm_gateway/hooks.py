from __future__ import annotations

import logging
import time
import uuid


logger = logging.getLogger("llm_gateway")
logging.basicConfig(level=logging.INFO)


class RequestTrace:
    def __init__(self):
        self.request_id = uuid.uuid4().hex[:12]
        self.start = time.time()

    def success(self):
        duration = round(time.time() - self.start, 3)
        logger.info(f"[{self.request_id}] success duration={duration}s")

    def failed(self, exc: Exception):
        duration = round(time.time() - self.start, 3)
        logger.error(
            f"[{self.request_id}] failed duration={duration}s error={repr(exc)}"
        )
