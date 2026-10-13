from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class RiskService:
    RADIUS_METERS = 50

    @staticmethod
    async def calculate(
        session: AsyncSession,
        route_request_id: int,
    ) -> dict:

        query = text("""
            WITH rota AS (
                SELECT
                    id AS calculated_route_id,
                    route_request_id,
                    geometry,
                    distance_km
                FROM calculated_routes
                WHERE route_request_id = :route_request_id
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            ),

            ocorrencias_proximas AS (
                SELECT
                    o.id,
                    o.rubrica,

                    ST_Distance(
                        COALESCE(
                            o.geog,
                            o.geom::geography
                        ),
                        r.geometry::geography
                    ) AS distancia_metros,

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
                    r.geometry::geography,
                    :radius_meters
                )
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
                                WHEN distancia_metros <= 100
                                    THEN 1.00

                                WHEN distancia_metros <= 200
                                    THEN 0.75

                                WHEN distancia_metros <= 300
                                    THEN 0.50

                                WHEN distancia_metros <= 400
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
        """)

        result = await session.execute(
            query,
            {
                "route_request_id": route_request_id,
                "radius_meters": RiskService.RADIUS_METERS,
            },
        )

        row = result.mappings().one_or_none()

        if row is None:
            raise ValueError(
                "Nenhuma rota calculada encontrada"
            )

        return {
            "calculated_route_id": row["calculated_route_id"],
            "quantidade_ocorrencias": row[
                "quantidade_ocorrencias"
            ],
            "pontuacao_original": int(
                row["pontuacao_original"]
            ),
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
            "raio_analise_metros": RiskService.RADIUS_METERS,
        }
