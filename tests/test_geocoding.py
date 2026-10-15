from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.geocoding import GeocodingService, GeocodingUnavailableError


@pytest.mark.asyncio
async def test_unconfigured_geocoder_does_not_make_a_request(monkeypatch):
    monkeypatch.setattr(settings, "nominatim_url", None)
    with patch("app.services.geocoding.httpx.AsyncClient") as factory:
        with pytest.raises(GeocodingUnavailableError):
            await GeocodingService.search("Avenida Paulista, São Paulo")
        factory.assert_not_called()


@pytest.mark.asyncio
async def test_geocoder_converts_valid_coordinates_and_passes_query(monkeypatch):
    monkeypatch.setattr(settings, "nominatim_url", "http://geocoder/")
    response = httpx.Response(
        200,
        json=[{"display_name": "Avenida Paulista", "lat": "-23.56", "lon": "-46.65"}],
        request=httpx.Request("GET", "http://geocoder/search"),
    )
    client = AsyncMock()
    client.get.return_value = response
    with patch("app.services.geocoding.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        places = await GeocodingService.search("Avenida Paulista, São Paulo")
    assert places[0].lat == -23.56
    assert places[0].lon == -46.65
    assert client.get.call_args.args[0] == "http://geocoder/search"
    assert client.get.call_args.kwargs["params"]["q"] == "Avenida Paulista, São Paulo"
    assert client.get.call_args.kwargs["params"]["countrycodes"] == "br"


@pytest.mark.parametrize(
    "error,status",
    [
        (GeocodingUnavailableError("not configured"), 503),
        (httpx.ReadTimeout("timeout"), 502),
        (ValueError("invalid coordinates"), 502),
    ],
)
def test_address_endpoint_reports_provider_failure(error, status):
    with (
        TestClient(app) as client,
        patch(
            "app.routers.places.GeocodingService.search", new_callable=AsyncMock
        ) as provider,
    ):
        provider.side_effect = error
        assert (
            client.get("/places", params={"q": "Avenida Paulista"}).status_code
            == status
        )


def test_address_endpoint_validates_query_and_returns_places():
    with (
        TestClient(app) as client,
        patch(
            "app.routers.places.GeocodingService.search", new_callable=AsyncMock
        ) as provider,
    ):
        for query in ("ab", "   ", "x" * 201):
            assert client.get("/places", params={"q": query}).status_code == 422
        provider.assert_not_awaited()
        provider.return_value = [
            {"display_name": "Paulista", "lat": -23.56, "lon": -46.65}
        ]
        response = client.get("/places", params={"q": " Paulista "})
        assert response.status_code == 200
        assert response.json()[0]["display_name"] == "Paulista"
        provider.assert_awaited_once_with("Paulista")


@pytest.mark.asyncio
async def test_reverse_uses_street_and_keeps_selected_coordinates():
    with patch.object(GeocodingService, "_request", new_callable=AsyncMock) as request:
        request.return_value = {
            "lat": "-23.9",
            "lon": "-46.9",
            "address": {
                "road": "Avenida Paulista",
                "house_number": "1000",
                "suburb": "Bela Vista",
                "city": "São Paulo",
            },
        }
        place = await GeocodingService.reverse(-23.56, -46.65)
        assert place.display_name == "Avenida Paulista, 1000, Bela Vista, São Paulo"
        assert (place.lat, place.lon) == (-23.56, -46.65)


@pytest.mark.asyncio
async def test_reverse_does_not_invent_an_address():
    with patch.object(GeocodingService, "_request", new_callable=AsyncMock) as request:
        request.return_value = {"error": "Unable to geocode"}
        assert await GeocodingService.reverse(0, 0) is None


def test_reverse_endpoint_validates_coordinates():
    with (
        TestClient(app) as client,
        patch.object(GeocodingService, "reverse", new_callable=AsyncMock) as provider,
    ):
        assert (
            client.get("/places/reverse", params={"lat": 91, "lon": 0}).status_code
            == 422
        )
        assert (
            client.get("/places/reverse", params={"lat": "nan", "lon": 0}).status_code
            == 422
        )
        provider.assert_not_awaited()
        provider.return_value = {
            "display_name": "Praça da Sé",
            "lat": -23.55,
            "lon": -46.63,
        }
        response = client.get("/places/reverse", params={"lat": -23.55, "lon": -46.63})
        assert response.status_code == 200
        assert response.json()["display_name"] == "Praça da Sé"
