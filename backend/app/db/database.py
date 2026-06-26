from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine = None
_session_maker = None


def _init_engine():
    global _engine, _session_maker
    if _engine is None:
        from app.core.config import get_settings
        url = get_settings().DATABASE_URL
        _engine = create_async_engine(url, echo=False)
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine, _session_maker


def get_engine():
    engine, _ = _init_engine()
    return engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    _, session_maker = _init_engine()
    async with session_maker() as session:
        yield session
