"""Run with TEST_DATABASE_URL pointing at a PostgreSQL database with PostGIS.

All fixtures use temporary tables on a single connection and roll back;
existing application tables and data are never modified.
"""

import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.services.risk_service import RiskService

pytestmark = [pytest.mark.postgis, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def spatial_session(monkeypatch):
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "Configure TEST_DATABASE_URL para testar a consulta real do PostGIS"
        )
    engine = create_async_engine(database_url, echo=False)
    monkeypatch.setattr(settings, "risk_radius_meters", 50)
    monkeypatch.setattr(settings, "occurrence_date_column", None)
    monkeypatch.setattr(settings, "occurrence_group_date_column", None)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        await connection.execute(
            text("""
            CREATE TEMP TABLE calculated_routes (
                id bigint PRIMARY KEY, route_request_id bigint,
                geometry geometry(LineString, 4326), distance_km double precision,
                created_at timestamptz DEFAULT now()
            ) ON COMMIT DROP
        """)
        )
        await connection.execute(
            text("""
            CREATE TEMP TABLE ocorrencias_stg (
                rubrica text, geog geography(Point, 4326),
                geom geometry(Point, 4326), ocorrido_em timestamptz
            ) ON COMMIT DROP
        """)
        )
        await connection.execute(
            text("""
            INSERT INTO calculated_routes (id, route_request_id, geometry, distance_km)
            VALUES (1, 42, ST_GeomFromText('LINESTRING(0 0, 0.01 0)', 4326), 2),
                   (2, 42, ST_GeomFromText('LINESTRING(10 10, 10.01 10)', 4326), 2),
                   (3, 43, ST_GeomFromText('LINESTRING(0 0, 0.01 0)', 4326), 0)
        """)
        )
        async with AsyncSession(
            bind=connection, join_transaction_mode="rollback_only"
        ) as session:
            yield session
        if transaction.is_active:
            await transaction.rollback()
    await engine.dispose()


async def occurrence(session, distance, rubrica="furto", fallback=False, age_days=1):
    # Project from the midpoint, perpendicular to an equatorial route.
    await session.execute(
        text("""
        INSERT INTO ocorrencias_stg (rubrica, geog, geom, ocorrido_em)
        SELECT :rubrica,
               CASE WHEN :fallback THEN NULL ELSE point END,
               CASE WHEN :fallback THEN point::geometry ELSE NULL END,
               now() - :age_days * INTERVAL '1 day'
        FROM (SELECT ST_Project(
            ST_GeogFromText('SRID=4326;POINT(0.005 0)'),
            CAST(:distance AS double precision), CAST(0 AS double precision)
        ) AS point) projected
    """),
        {
            "rubrica": rubrica,
            "distance": float(distance),
            "fallback": fallback,
            "age_days": age_days,
        },
    )


async def test_exact_route_and_geometry_fallback(spatial_session):
    await occurrence(spatial_session, 0, "roubo", fallback=True)
    await occurrence(spatial_session, 51, "homicídio")
    main = await RiskService.calculate(spatial_session, 1)
    alternate = await RiskService.calculate(spatial_session, 2)
    assert main["quantidade_ocorrencias"] == 1
    assert main["pontuacao_original"] == 3
    assert main["pontos_ajustados_por_km"] == 1.5
    assert alternate["quantidade_ocorrencias"] == 0
    assert alternate["calculated_route_id"] == 2


async def test_distance_weights_inside_radius(spatial_session):
    for distance in (5, 15, 25, 35, 45, 50.01):
        await occurrence(spatial_session, distance)
    risk = await RiskService.calculate(spatial_session, 1)
    assert risk["quantidade_ocorrencias"] == 5
    assert risk["pontuacao_original"] == 5
    assert risk["pontuacao_ajustada"] == 2.6
    assert risk["pontos_ajustados_por_km"] == 1.3


@pytest.mark.parametrize("distance,count", [(49.99, 1), (50.01, 0)])
async def test_radius_boundary(spatial_session, distance, count):
    await occurrence(spatial_session, distance)
    risk = await RiskService.calculate(spatial_session, 1)
    assert risk["quantidade_ocorrencias"] == count


async def test_zero_length_and_null_geometry(spatial_session):
    await spatial_session.execute(
        text("INSERT INTO ocorrencias_stg (rubrica) VALUES ('roubo')")
    )
    risk = await RiskService.calculate(spatial_session, 3)
    assert risk["quantidade_ocorrencias"] == 0
    assert risk["pontos_originais_por_km"] is None
    assert risk["pontos_ajustados_por_km"] is None
    with pytest.raises(ValueError, match="Nenhuma rota"):
        await RiskService.calculate(spatial_session, 999)


async def test_temporal_window_excludes_old_future_and_undated_events(
    spatial_session, monkeypatch
):
    monkeypatch.setattr(settings, "occurrence_date_column", "ocorrido_em")
    monkeypatch.setattr(settings, "risk_window_days", 30)
    for age_days in (1, 31, -1):
        await occurrence(spatial_session, 0, age_days=age_days)
    await spatial_session.execute(
        text("""
        INSERT INTO ocorrencias_stg (rubrica, geog)
        VALUES ('roubo', ST_GeogFromText('SRID=4326;POINT(0.005 0)'))
    """)
    )
    risk = await RiskService.calculate(spatial_session, 1)
    assert risk["quantidade_ocorrencias"] == 1
    assert risk["filtro_temporal_aplicado"]
    assert (risk["periodo_fim"] - risk["periodo_inicio"]).days == 30


async def test_concurrent_analyses_do_not_choose_the_latest_route(spatial_session):
    await occurrence(spatial_session, 0, "roubo")
    # Separate sessions sharing the fixture connection; queries are serialized by
    # the driver, while each request keeps the explicit route ID it received.
    async with AsyncSession(bind=spatial_session.bind) as other:
        first, second = await asyncio.gather(
            RiskService.calculate(spatial_session, 1), RiskService.calculate(other, 2)
        )
    assert first["calculated_route_id"] == 1
    assert first["quantidade_ocorrencias"] == 1
    assert second["calculated_route_id"] == 2
    assert second["quantidade_ocorrencias"] == 0


async def test_risk_is_grouped_by_crime_and_matches_total(spatial_session):
    await occurrence(spatial_session, 0, "roubo")
    await occurrence(spatial_session, 25, " ROUBO ")
    await occurrence(spatial_session, 45, "furto")
    await occurrence(spatial_session, 51, "homicídio")
    risk = await RiskService.calculate(spatial_session, 1)
    crimes = risk["riscos_por_crime"]
    assert [item["crime"] for item in crimes] == ["roubo", "furto"]
    assert crimes[0] == {
        "crime": "roubo",
        "quantidade_ocorrencias": 2,
        "pontuacao_original": 6,
        "pontuacao_ajustada": 4.5,
        "pontos_originais_por_km": 3,
        "pontos_ajustados_por_km": 2.25,
    }
    assert (
        sum(item["quantidade_ocorrencias"] for item in crimes)
        == risk["quantidade_ocorrencias"]
    )
    assert (
        sum(item["pontuacao_original"] for item in crimes) == risk["pontuacao_original"]
    )
    assert sum(item["pontuacao_ajustada"] for item in crimes) == pytest.approx(
        risk["pontuacao_ajustada"]
    )
    assert (await RiskService.calculate(spatial_session, 2))["riscos_por_crime"] == []


async def test_crime_with_missing_name_and_zero_length(spatial_session):
    await occurrence(spatial_session, 0, None)
    await occurrence(spatial_session, 0, "  ")
    risk = await RiskService.calculate(spatial_session, 3)
    assert len(risk["riscos_por_crime"]) == 1
    crime = risk["riscos_por_crime"][0]
    assert crime["crime"] == "Não informado"
    assert crime["quantidade_ocorrencias"] == 2
    assert crime["pontos_ajustados_por_km"] is None
    assert crime["pontos_originais_por_km"] is None


async def test_month_groups_preserve_undated_events_and_totals(
    spatial_session, monkeypatch
):
    monkeypatch.setattr(settings, "occurrence_group_date_column", "ocorrido_em")
    await occurrence(spatial_session, 0, "roubo", age_days=1)
    await occurrence(spatial_session, 20, "furto", age_days=70)
    await spatial_session.execute(
        text(
            "INSERT INTO ocorrencias_stg (rubrica, geog) VALUES ('furto', ST_GeogFromText('SRID=4326;POINT(0.005 0)'))"
        )
    )
    risk = await RiskService.calculate(spatial_session, 1)
    groups = risk["ocorrencias_por_mes"]
    assert risk["data_agrupamento_configurada"]
    assert len(groups) == 3
    assert groups[-1]["mes"] is None
    assert groups[-1]["quantidade_ocorrencias"] == 1
    assert (
        sum(group["quantidade_ocorrencias"] for group in groups)
        == risk["quantidade_ocorrencias"]
    )
    assert sum(group["pontuacao_ajustada"] for group in groups) == pytest.approx(
        risk["pontuacao_ajustada"]
    )
    assert all(
        sum(crime["quantidade_ocorrencias"] for crime in group["crimes"])
        == group["quantidade_ocorrencias"]
        for group in groups
    )
