from pydantic import BaseModel, Field

from pydantic import BaseModel, Field

from app.models.route_request import TransportMode


class RouteRequestCreate(BaseModel):
    origin_lat: float = Field(ge=-90, le=90)
    origin_lon: float = Field(ge=-180, le=180)

    destination_lat: float = Field(ge=-90, le=90)
    destination_lon: float = Field(ge=-180, le=180)

    transport_mode: TransportMode = TransportMode.AUTO
