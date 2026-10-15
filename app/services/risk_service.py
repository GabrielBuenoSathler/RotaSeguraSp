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
        group_column = (
            settings.occurrence_group_date_column or settings.occurrence_date_column
        )
        month_expression = (
            f"DATE_TRUNC('month', o.\"{group_column}\"::timestamp)::date"
            if group_column
            else "NULL::date"
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
                    COALESCE(NULLIF(LOWER(BTRIM(o.rubrica)), ''), 'Não informado') AS crime,
                    __MONTH_EXPRESSION__ AS mes,
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

            ocorrencias_ponderadas AS (
                SELECT *, peso * CASE
                    WHEN distancia_metros <= :radius_meters * 0.2 THEN 1.00
                    WHEN distancia_metros <= :radius_meters * 0.4 THEN 0.75
                    WHEN distancia_metros <= :radius_meters * 0.6 THEN 0.50
                    WHEN distancia_metros <= :radius_meters * 0.8 THEN 0.25
                    ELSE 0.10
                END AS pontos_ajustados
                FROM ocorrencias_proximas
            ),
            pontuacao AS (
                SELECT COUNT(*) AS quantidade_ocorrencias,
                       COALESCE(SUM(peso), 0) AS pontuacao_original,
                       COALESCE(SUM(pontos_ajustados), 0) AS pontuacao_ajustada
                FROM ocorrencias_ponderadas
            ),
            pontuacao_por_mes_crime AS (
                SELECT mes, crime, COUNT(*) AS quantidade_ocorrencias,
                       SUM(pontos_ajustados) AS pontuacao_ajustada
                FROM ocorrencias_ponderadas
                GROUP BY mes, crime
            ),
            pontuacao_por_mes AS (
                SELECT mes, SUM(quantidade_ocorrencias) AS quantidade_ocorrencias,
                       SUM(pontuacao_ajustada) AS pontuacao_ajustada,
                       jsonb_agg(jsonb_build_object(
                           'crime', crime,
                           'quantidade_ocorrencias', quantidade_ocorrencias,
                           'pontuacao_ajustada', ROUND(pontuacao_ajustada, 2)
                       ) ORDER BY pontuacao_ajustada DESC, crime) AS crimes
                FROM pontuacao_por_mes_crime
                GROUP BY mes
            ),
            pontuacao_por_crime AS (
                SELECT crime, COUNT(*) AS quantidade_ocorrencias,
                       SUM(peso) AS pontuacao_original,
                       SUM(pontos_ajustados) AS pontuacao_ajustada
                FROM ocorrencias_ponderadas
                GROUP BY crime
            )

            SELECT
                r.calculated_route_id,
                r.route_request_id,
                r.distance_km,

                COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'mes', m.mes,
                        'quantidade_ocorrencias', m.quantidade_ocorrencias,
                        'pontuacao_ajustada', ROUND(m.pontuacao_ajustada, 2),
                        'crimes', m.crimes
                    ) ORDER BY m.mes DESC NULLS LAST)
                    FROM pontuacao_por_mes m
                ), '[]'::jsonb) AS ocorrencias_por_mes,
                p.quantidade_ocorrencias,
                p.pontuacao_original,
                p.pontuacao_ajustada,
                COALESCE((
                    SELECT jsonb_agg(jsonb_build_object(
                        'crime', c.crime,
                        'quantidade_ocorrencias', c.quantidade_ocorrencias,
                        'pontuacao_original', c.pontuacao_original,
                        'pontuacao_ajustada', ROUND(c.pontuacao_ajustada, 2),
                        'pontos_originais_por_km', ROUND(
                            (c.pontuacao_original / NULLIF(r.distance_km, 0))::numeric, 2),
                        'pontos_ajustados_por_km', ROUND(
                            (c.pontuacao_ajustada / NULLIF(r.distance_km, 0))::numeric, 2)
                    ) ORDER BY c.pontuacao_ajustada DESC, c.crime)
                    FROM pontuacao_por_crime c
                ), '[]'::jsonb) AS riscos_por_crime,

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
        """.replace("__DATE_FILTER__", date_filter).replace(
                "__MONTH_EXPRESSION__", month_expression
            )
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
            "riscos_por_crime": row["riscos_por_crime"],
            "ocorrencias_por_mes": row["ocorrencias_por_mes"],
            "data_agrupamento_configurada": bool(group_column),
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
