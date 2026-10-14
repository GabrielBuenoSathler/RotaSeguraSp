import pytest
from pydantic import ValidationError

from app.schema import RouteRequestCreate


@pytest.fixture
def coordinates():
    return {
        "origin_lat": -23.55,
        "origin_lon": -46.63,
        "destination_lat": -23.56,
        "destination_lon": -46.64,
    }


def test_route_defaults_to_car(coordinates):
    assert RouteRequestCreate(**coordinates).transport_mode.value == "auto"


@pytest.mark.parametrize("mode", ["auto", "bicycle", "pedestrian", "motorcycle"])
def test_ui_transport_modes_are_accepted(coordinates, mode):
    assert (
        RouteRequestCreate(**coordinates, transport_mode=mode).transport_mode.value
        == mode
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("origin_lat", 90.01),
        ("origin_lat", -90.01),
        ("destination_lat", 90.01),
        ("destination_lat", -90.01),
        ("origin_lon", 180.01),
        ("origin_lon", -180.01),
        ("destination_lon", 180.01),
        ("destination_lon", -180.01),
    ],
)
def test_coordinates_outside_geographic_bounds_are_rejected(coordinates, field, value):
    coordinates[field] = value
    with pytest.raises(ValidationError):
        RouteRequestCreate(**coordinates)


def test_unknown_transport_mode_is_rejected(coordinates):
    with pytest.raises(ValidationError):
        RouteRequestCreate(**coordinates, transport_mode="flying")
