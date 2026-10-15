from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.risk_service import RiskService
from app.services.valhala import ValhallaService


@pytest.mark.asyncio
async def test_risk_converts_database_numbers_and_preserves_missing_density():
    cells = [
        {"lat": -23.55, "lon": -46.63, "mes": None, "grupo": "pessoa", "quantidade": 3}
    ]
    row = {
        "mapa_calor": cells,
        "ocorrencias_por_mes": [],
        "data_agrupamento_configurada": False,
        "riscos_por_crime": [],
        "calculated_route_id": 42,
        "quantidade_ocorrencias": 3,
        "pontuacao_original": Decimal(9),
        "pontuacao_ajustada": Decimal("6.125"),
        "pontos_originais_por_km": None,
        "pontos_ajustados_por_km": Decimal("2.50"),
    }
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = row
    session.execute.return_value = result

    risk = await RiskService.calculate(session, 42)

    assert risk == {
        "mapa_calor": cells,
        "ocorrencias_por_mes": [],
        "data_agrupamento_configurada": False,
        "riscos_por_crime": [],
        "calculated_route_id": 42,
        "quantidade_ocorrencias": 3,
        "pontuacao_original": 9,
        "pontuacao_ajustada": 6.12,
        "pontos_originais_por_km": None,
        "pontos_ajustados_por_km": 2.5,
        "raio_analise_metros": 50,
        "metodologia": "exposicao-v2",
        "fonte": "Base de ocorrências importada pelo administrador",
        "atualizado_em": None,
        "periodo_inicio": None,
        "periodo_fim": None,
        "filtro_temporal_aplicado": False,
    }
    assert session.execute.call_args.args[1] == {
        "calculated_route_id": 42,
        "radius_meters": 50,
    }


@pytest.mark.asyncio
async def test_risk_reports_missing_calculated_route():
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = None
    session.execute.return_value = result
    with pytest.raises(ValueError, match="Nenhuma rota calculada"):
        await RiskService.calculate(session, 99)


@pytest.mark.asyncio
async def test_valhalla_sends_coordinates_mode_and_units():
    response = httpx.Response(
        200,
        json={"trip": {"summary": {"length": 2.4}}},
        request=httpx.Request("POST", "http://routing/route"),
    )
    client = AsyncMock()
    client.post.return_value = response
    with patch("app.services.valhala.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        result = await ValhallaService("http://routing").calculate_route(
            -23.55, -46.63, -23.56, -46.64, "bicycle"
        )
    client.post.assert_awaited_once_with(
        "http://routing/route",
        json={
            "locations": [
                {"lat": -23.55, "lon": -46.63},
                {"lat": -23.56, "lon": -46.64},
            ],
            "costing": "bicycle",
            "units": "kilometers",
        },
    )
    assert result["trip"]["summary"]["length"] == 2.4


@pytest.mark.asyncio
async def test_valhalla_propagates_http_failure():
    client = AsyncMock()
    client.post.return_value = httpx.Response(
        503, request=httpx.Request("POST", "http://routing/route")
    )
    with patch("app.services.valhala.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        with pytest.raises(httpx.HTTPStatusError):
            await ValhallaService("http://routing").calculate_route(0, 0, 1, 1)
