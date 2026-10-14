from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_session
from app.main import app
from app.models.route_request import TransportMode
from app.routers.router_requests_v import decode_valhalla_shape


def encode_points(points):
    previous = (0, 0)
    output = []
    for lat, lon in points:
        current = (round(lat * 1_000_000), round(lon * 1_000_000))
        for value, old in zip(current, previous, strict=True):
            delta = value - old
            number = ~(delta << 1) if delta < 0 else delta << 1
            while number >= 0x20:
                output.append(chr((0x20 | (number & 0x1F)) + 63))
                number >>= 5
            output.append(chr(number + 63))
        previous = current
    return "".join(output)


def trip(points=None, **summary):
    return {
        "summary": {"length": 2.4, "time": 300, **summary},
        "legs": [
            {"shape": encode_points(points or [(-23.55, -46.63), (-23.56, -46.64)])}
        ],
    }


@pytest.fixture
def session():
    value = AsyncMock()
    value.add = MagicMock()
    result = MagicMock()
    result.one_or_none.return_value = SimpleNamespace(
        id=42,
        origin_lat=-23.55,
        origin_lon=-46.63,
        destination_lat=-23.56,
        destination_lon=-46.64,
        transport_mode=TransportMode.AUTO,
    )
    value.execute.return_value = result

    async def flush():
        for index, call in enumerate(value.add.call_args_list, start=7):
            call.args[0].id = index

    async def refresh(record):
        record.id = 42
        record.created_at = datetime.now(UTC)

    value.flush.side_effect = flush
    value.refresh.side_effect = refresh
    return value


@pytest.fixture
def client(session):
    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()


@pytest.fixture
def providers():
    with (
        patch("app.routers.router_requests_v.ValhallaService") as routing,
        patch(
            "app.routers.router_requests_v.RiskService.calculate",
            new_callable=AsyncMock,
        ) as risk,
    ):
        routing.return_value.calculate_route = AsyncMock(return_value={"trip": trip()})
        risk.side_effect = ValueError("Risco indisponível")
        yield routing.return_value.calculate_route, risk


def test_create_request_and_validate_coordinates(client, session):
    payload = {
        "origin_lat": -23.55,
        "origin_lon": -46.63,
        "destination_lat": -23.56,
        "destination_lon": -46.64,
    }
    response = client.post("/rota/", json=payload)
    assert response.status_code == 201
    assert response.json()["id"] == 42
    assert client.post("/rota/", json={**payload, "origin_lat": 100}).status_code == 422
    session.commit.assert_awaited_once()


def test_create_failure_rolls_back(client, session):
    session.commit.side_effect = SQLAlchemyError("unavailable")
    response = client.post(
        "/rota/",
        json={
            "origin_lat": 0,
            "origin_lon": 0,
            "destination_lat": 1,
            "destination_lon": 1,
        },
    )
    assert response.status_code == 500
    session.rollback.assert_awaited_once()


def test_missing_request_does_not_call_provider(client, session, providers):
    session.execute.return_value.one_or_none.return_value = None
    assert client.post("/rota/42/calculate").status_code == 404
    providers[0].assert_not_awaited()


@pytest.mark.parametrize(
    "exception,status",
    [
        (httpx.ConnectError("offline"), 502),
        (httpx.ReadTimeout("timeout"), 504),
        (ValueError("invalid JSON"), 502),
    ],
)
def test_provider_failures(client, providers, exception, status):
    providers[0].side_effect = exception
    assert client.post("/rota/42/calculate").status_code == status


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"trip": {}},
        {"trip": trip(length=-1)},
        {"trip": trip(time=float("inf"))},
        {"trip": {"summary": {"length": 1, "time": 1}, "legs": [{"shape": "_"}]}},
        {"trip": {"summary": {"length": 1, "time": 1}, "legs": []}},
        [],
        None,
    ],
)
def test_malformed_routes_are_rejected(client, providers, session, response):
    providers[0].return_value = response
    assert client.post("/rota/42/calculate").status_code == 502
    session.add.assert_not_called()


def test_alternatives_use_their_own_ids_even_after_risk_failure(
    client, providers, session
):
    providers[0].return_value = {
        "trip": trip(),
        "alternates": [{"trip": trip([(-23.55, -46.63), (-23.57, -46.64)])}],
    }

    # Simulate expiration of ORM objects after rollback.
    async def rollback():
        for call in session.add.call_args_list:
            call.args[0].id = -1

    session.rollback.side_effect = rollback
    response = client.post("/rota/42/calculate")
    assert response.status_code == 200
    data = response.json()
    assert data["route"]["calculated_route_id"] == 7
    assert data["alternatives"][0]["route"]["calculated_route_id"] == 8
    assert not data["risk"]["status"]["success"]
    assert [call.args[1] for call in providers[1].await_args_list] == [7, 8]
    assert data["route"]["geometry"]["coordinates"][0] == [-46.63, -23.55]


def test_invalid_and_duplicate_alternatives_are_ignored(client, providers):
    providers[0].return_value = {"trip": trip(), "alternates": [{"trip": trip()}, {}]}
    response = client.post("/rota/42/calculate")
    assert response.status_code == 200
    assert response.json()["alternatives"] == []


def test_successful_analysis_is_serialized_for_each_option(client, providers):
    providers[0].return_value = {
        "trip": trip(),
        "alternates": [{"trip": trip([(-23.55, -46.63), (-23.57, -46.64)])}],
    }

    async def calculate_risk(session, route_id):
        return {
            "calculated_route_id": route_id,
            "quantidade_ocorrencias": 2,
            "pontuacao_original": 4,
            "pontuacao_ajustada": 2.5,
            "pontos_originais_por_km": 1.67,
            "pontos_ajustados_por_km": 1.04,
            "raio_analise_metros": 50,
            "metodologia": "exposicao-v2",
            "fonte": "Base de teste",
            "atualizado_em": None,
            "periodo_inicio": None,
            "periodo_fim": None,
            "filtro_temporal_aplicado": False,
        }

    providers[1].side_effect = calculate_risk
    response = client.post("/rota/42/calculate")
    assert response.status_code == 200
    data = response.json()
    for option in [data, *data["alternatives"]]:
        assert option["risk"]["status"]["success"]
        assert (
            option["route"]["calculated_route_id"]
            == option["risk"]["result"]["calculated_route_id"]
        )
        assert option["risk"]["result"]["pontuacao_ajustada"] == 2.5
    assert providers[0].call_args.kwargs["alternates"] == 2


def test_persist_failure_does_not_report_success(client, providers, session):
    session.commit.side_effect = SQLAlchemyError("unavailable")
    assert client.post("/rota/42/calculate").status_code == 500
    providers[1].assert_not_awaited()
    session.rollback.assert_awaited_once()


def test_polyline6_known_coordinates():
    # A literal polyline for (0, 0) and (0.01, 0), with precision 6.
    assert decode_valhalla_shape("??_pR?") == [(0, 0), (0.01, 0)]


@pytest.mark.parametrize("shape", ["_", "??_", "!!", "~~~~~~~?"])
def test_invalid_polylines(shape):
    with pytest.raises(ValueError):
        decode_valhalla_shape(shape)
