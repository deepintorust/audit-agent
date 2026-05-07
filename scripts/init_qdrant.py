from __future__ import annotations

from src.app.settings import get_settings
from src.vectorstore.qdrant import QdrantStore


def main() -> None:
    s = get_settings()
    store = QdrantStore(s)
    store.ensure_collection(vector_size=s.embed_dim)
    store.ensure_payload_indexes()


if __name__ == "__main__":
    main()

