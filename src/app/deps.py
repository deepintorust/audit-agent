from __future__ import annotations

from functools import lru_cache

from src.app.settings import Settings, get_settings
from src.db.session import Database
from src.mq.rabbit import Rabbit
from src.storage.s3 import S3Storage
from src.vectorstore.qdrant import QdrantStore
from src.embedding.client import EmbeddingClient


@lru_cache
def settings() -> Settings:
    return get_settings()


@lru_cache
def db() -> Database:
    return Database(settings())


@lru_cache
def rabbit() -> Rabbit:
    return Rabbit(settings())


@lru_cache
def storage() -> S3Storage:
    return S3Storage(settings())


@lru_cache
def qdrant() -> QdrantStore:
    return QdrantStore(settings())


@lru_cache
def embedding() -> EmbeddingClient:
    return EmbeddingClient(settings())
