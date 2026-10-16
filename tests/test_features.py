from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.mark.parametrize("enabled", [True, False])
def test_public_features_follow_flags_without_exposing_provider_url(
    monkeypatch, enabled
):
    monkeypatch.setattr(settings, "feature_geocoding", enabled)
    monkeypatch.setattr(settings, "feature_route_alternatives", enabled)
    monkeypatch.setattr(settings, "nominatim_url", "https://private-provider.example")
    with TestClient(app) as client:
        response = client.get("/features")
    assert response.json() == {"geocoding": enabled, "route_alternatives": enabled}
    assert response.headers["cache-control"] == "no-store"


def test_features_report_missing_provider_and_zero_alternatives(monkeypatch):
    monkeypatch.setattr(settings, "route_alternates", 0)
    with TestClient(app) as client:
        assert client.get("/features").json() == {
            "geocoding": False,
            "route_alternatives": False,
        }


@pytest.mark.parametrize(
    "path", ["/places?q=Paulista", "/places/reverse?lat=-23.5&lon=-46.6"]
)
def test_disabled_geocoding_blocks_direct_api_calls(monkeypatch, path):
    monkeypatch.setattr(settings, "feature_geocoding", False)
    monkeypatch.setattr(settings, "nominatim_url", "https://provider.example")
    with (
        TestClient(app) as client,
        patch("app.services.geocoding.httpx.AsyncClient") as provider,
    ):
        assert client.get(path).status_code == 503
        provider.assert_not_called()
