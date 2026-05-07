from __future__ import annotations

from collections.abc import Awaitable, Callable

from src.mq.messages import FileEvent
from src.mq.topology import (
    QUEUE_CHUNK,
    QUEUE_EMBED,
    QUEUE_EXTRACT,
    QUEUE_FUSE,
    QUEUE_INDEX,
    QUEUE_PARSE,
    QUEUE_STORE,
)
from src.workers.store_worker import handle_store
from src.workers.parse_worker import handle_parse
from src.workers.extract_worker import handle_extract
from src.workers.fusion_worker import handle_fuse
from src.workers.chunk_worker import handle_chunk
from src.workers.embed_worker import handle_embed
from src.workers.index_worker import handle_index

Handler = Callable[[FileEvent], Awaitable[None]]


def get_handler_for_queue(queue: str) -> Handler:
    return {
        QUEUE_STORE: handle_store,
        QUEUE_PARSE: handle_parse,
        QUEUE_EXTRACT: handle_extract,
        QUEUE_FUSE: handle_fuse,
        QUEUE_CHUNK: handle_chunk,
        QUEUE_EMBED: handle_embed,
        QUEUE_INDEX: handle_index,
    }[queue]

