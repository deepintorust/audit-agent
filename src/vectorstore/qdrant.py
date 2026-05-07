from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PayloadSchemaType, VectorParams

from src.app.settings import Settings


class QdrantStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    def ensure_collection(self, vector_size: int) -> None:
        name = self.settings.qdrant_collection
        if self.client.collection_exists(name):
            return
        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def ensure_payload_indexes(self) -> None:
        name = self.settings.qdrant_collection
        # Payload indexes accelerate filter queries; safe to call repeatedly.
        fields = {
            "fileuuid": PayloadSchemaType.KEYWORD,
            "project": PayloadSchemaType.KEYWORD,
            "company": PayloadSchemaType.KEYWORD,
            "phase": PayloadSchemaType.KEYWORD,
            "category": PayloadSchemaType.KEYWORD,
            "subcategory": PayloadSchemaType.KEYWORD,
        }
        for field, schema_type in fields.items():
            try:
                self.client.create_payload_index(
                    collection_name=name,
                    field_name=field,
                    field_schema=schema_type,
                )
            except Exception:
                # If already exists or unsupported in this version, ignore.
                pass
