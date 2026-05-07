from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.app.settings import Settings


class Database:
    def __init__(self, settings: Settings):
        dsn = (
            f"mysql+aiomysql://{settings.mysql_user}:{settings.mysql_password}"
            f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
        )
        self._engine: AsyncEngine = create_async_engine(
            dsn,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self._sessionmaker = async_sessionmaker(self._engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncSession:
        async with self._sessionmaker() as session:
            yield session

