from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, registry


mapper_registry = registry()


@mapper_registry.mapped_as_dataclass
class RouteRequest:
    __tablename__ = "route_requests"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        init=False,
    )

    origin: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )

    destination: Mapped[object] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        init=False,
    )


























































