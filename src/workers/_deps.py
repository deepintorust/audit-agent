from __future__ import annotations

from functools import lru_cache

from src.app.settings import get_settings
from src.db.session import Database
from src.mq.rabbit import Rabbit
from src.storage.s3 import S3Storage
from src.vectorstore.qdrant import QdrantStore


@lru_cache
def settings():
    return get_settings()


@lru_cache
def db():
    return Database(settings())


@lru_cache
def rabbit():
    return Rabbit(settings())


@lru_cache
def storage():
    return S3Storage(settings())


@lru_cache
def qdrant():
    return QdrantStore(settings())

