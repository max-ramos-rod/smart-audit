from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
