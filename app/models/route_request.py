from datetime import datetime
from enum import Enum

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import Mapped, mapped_column


from app.core.database import Base


class TransportMode(str, Enum):
    AUTO = "auto"
    BICYCLE = "bicycle"
    BUS = "bus"
    TRUCK = "truck"
    TAXI = "taxi"
    MOTOR_SCOOTER = "motor_scooter"
    MOTORCYCLE = "motorcycle"
    PEDESTRIAN = "pedestrian"
    BIKESHARE = "bikeshare"
    MULTIMODAL = "multimodal"


def enum_values(enum_class: type[Enum]) -> list[str]:

    return [member.value for member in enum_class]


class RouteRequest(Base):
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

    transport_mode: Mapped[TransportMode] = mapped_column(
        PGEnum(
            TransportMode,
            name="transport_mode",
            values_callable=enum_values,
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        init=False,
    )
























































































































































