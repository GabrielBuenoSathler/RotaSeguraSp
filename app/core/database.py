from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from app.core.config import settings

DATABASE_URL = URL.create(
    "postgresql+asyncpg",
    username=settings.postgres_user,
    password=settings.postgres_password,
    host=settings.postgres_host,
    port=settings.postgres_port,
    database=settings.postgres_database,
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.sql_echo,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(MappedAsDataclass, DeclarativeBase):
    pass


async def get_session():
    async with SessionLocal() as session:
        yield session
