from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PayloadSchemaType, VectorParams

from src.app.settings import Settings


class QdrantStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

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

    # ------------------ convenience API ------------------
    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> None:
        if self.client.collection_exists(collection_name):
            return
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )

    def upsert_points(
        self,
        collection_name: str,
        ids: list,
        vectors: list[list[float]],
        payloads: list[dict] | None = None,
    ) -> None:
        # Qdrant client expects list of dicts or Batch -- use upload_records style
        points = [
            {"id": pid, "vector": vec, "payload": payload}
            for pid, vec, payload in zip(ids, vectors, payloads or [{} for _ in ids])
        ]
        self.client.upsert(collection_name=collection_name, points=points)

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 5,
        offset: int | None = None,
        query_filter: object | None = None,
        score_threshold: float | None = None,
    ):
        """Search wrapper: returns list of hits (client-dependent objects).

        Accepts either qdrant_client models.Filter for `query_filter` or None.
        Passes through `score_threshold` if supported by client.
        """
        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            offset=offset,
            score_threshold=score_threshold,
        )

    def delete_by_ids(self, collection_name: str, ids: list) -> None:
        self.client.delete(collection_name=collection_name, point_ids=ids)

    def delete_by_filter(self, collection_name: str, query_filter) -> None:
        # use http delete with FilterSelector when available
        try:
            self.client.delete(collection_name=collection_name, filter=query_filter)
        except Exception:
            # best-effort fallback
            self.client.http.delete(
                collection_name=collection_name, body={"filter": query_filter}
            )
