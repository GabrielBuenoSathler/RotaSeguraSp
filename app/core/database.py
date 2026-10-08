from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


DATABASE_URL = (
    f"postgresql://"
    f"{settings.postgres_user}:"
    f"{settings.postgres_password}@"
    f"{settings.postgres_host}:"
    f"{settings.postgres_port}/"
    f"Criminalidade"
)


engine = create_async_engine(DATABASE_URL)


class Base(DeclarativeBase):
    pass















