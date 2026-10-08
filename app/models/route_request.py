from datetime import datetime

from sqlalchemy import DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.core.database import Base


class RouteRequest(Base):
    __tablename__ = "route_requests"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    origin: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False
    )

    destination: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
