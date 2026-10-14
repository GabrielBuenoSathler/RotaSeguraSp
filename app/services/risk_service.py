from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class RiskService:
    @staticmethod
    async def calculate(
        session: AsyncSession,
        calculated_route_id: int,
    ) -> dict:
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=settings.risk_window_days)
        # Only a validated administrator-configured identifier is interpolated.
        date_filter = ""
        if settings.occurrence_date_column:
            column = settings.occurrence_date_column
            date_filter = (
                f'AND o."{column}" >= :period_start AND o."{column}" <= :period_end'
            )
        query = text(
            """
            WITH rota AS (
                SELECT
                    id AS calculated_route_id,
                    route_request_id,
                    geometry::geography AS geography,
                    distance_km
                FROM calculated_routes
                WHERE id = :calculated_route_id
            ),

            ocorrencias_proximas AS (
                SELECT
                    ST_Distance(
                            COALESCE(o.geog, o.geom::geography),
                            r.geography
                        )
                    AS distancia_metros,

                    CASE
                        WHEN o.rubrica ILIKE '%estupro%'
                            THEN 5

                        WHEN o.rubrica ILIKE '%feminicídio%'
                            THEN 5

                        WHEN o.rubrica ILIKE '%latrocínio%'
                            THEN 5

                        WHEN o.rubrica ILIKE '%homicídio%'
                            THEN 5

                        WHEN o.rubrica ILIKE '%roubo%'
                            THEN 3

                        WHEN o.rubrica ILIKE '%extorsão mediante sequestro%'
                            THEN 3

                        WHEN o.rubrica ILIKE '%arma de fogo%'
                            THEN 3

                        WHEN o.rubrica ILIKE '%lesão corporal%'
                            THEN 2

                        WHEN o.rubrica ILIKE '%tráfico%'
                            THEN 2

                        WHEN o.rubrica ILIKE '%furto%'
                            THEN 1

                        ELSE 1
                    END AS peso

                FROM ocorrencias_stg o
                CROSS JOIN rota r

                WHERE COALESCE(
                    o.geog,
                    o.geom::geography
                ) IS NOT NULL

                AND ST_DWithin(
                    COALESCE(
                        o.geog,
                        o.geom::geography
                    ),
                    r.geography,
                    :radius_meters
                )
                __DATE_FILTER__
            ),

            pontuacao AS (
                SELECT
                    COUNT(*) AS quantidade_ocorrencias,

                    COALESCE(
                        SUM(peso),
                        0
                    ) AS pontuacao_original,

                    COALESCE(
                        SUM(
                            peso *
                            CASE
                                WHEN distancia_metros <= :radius_meters * 0.2
                                    THEN 1.00

                                WHEN distancia_metros <= :radius_meters * 0.4
                                    THEN 0.75

                                WHEN distancia_metros <= :radius_meters * 0.6
                                    THEN 0.50

                                WHEN distancia_metros <= :radius_meters * 0.8
                                    THEN 0.25

                                ELSE 0.10
                            END
                        ),
                        0
                    ) AS pontuacao_ajustada

                FROM ocorrencias_proximas
            )

            SELECT
                r.calculated_route_id,
                r.route_request_id,
                r.distance_km,

                p.quantidade_ocorrencias,
                p.pontuacao_original,
                p.pontuacao_ajustada,

                ROUND(
                    (
                        p.pontuacao_original
                        / NULLIF(r.distance_km, 0)
                    )::numeric,
                    2
                ) AS pontos_originais_por_km,

                ROUND(
                    (
                        p.pontuacao_ajustada
                        / NULLIF(r.distance_km, 0)
                    )::numeric,
                    2
                ) AS pontos_ajustados_por_km

            FROM rota r
            CROSS JOIN pontuacao p
        """.replace("__DATE_FILTER__", date_filter)
        )

        result = await session.execute(
            query,
            {
                "calculated_route_id": calculated_route_id,
                "radius_meters": settings.risk_radius_meters,
                **(
                    {"period_start": period_start, "period_end": period_end}
                    if date_filter
                    else {}
                ),
            },
        )

        row = result.mappings().one_or_none()

        if row is None:
            raise ValueError("Nenhuma rota calculada encontrada")

        return {
            "calculated_route_id": row["calculated_route_id"],
            "quantidade_ocorrencias": row["quantidade_ocorrencias"],
            "pontuacao_original": int(row["pontuacao_original"]),
            "pontuacao_ajustada": round(
                float(row["pontuacao_ajustada"]),
                2,
            ),
            "pontos_originais_por_km": (
                float(row["pontos_originais_por_km"])
                if row["pontos_originais_por_km"] is not None
                else None
            ),
            "pontos_ajustados_por_km": (
                float(row["pontos_ajustados_por_km"])
                if row["pontos_ajustados_por_km"] is not None
                else None
            ),
            "raio_analise_metros": settings.risk_radius_meters,
            "metodologia": "exposicao-v2",
            "fonte": settings.dataset_source,
            "atualizado_em": settings.dataset_updated_at,
            "periodo_inicio": period_start if date_filter else None,
            "periodo_fim": period_end if date_filter else None,
            "filtro_temporal_aplicado": bool(date_filter),
        }
