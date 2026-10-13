import httpx

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.elements import WKTElement
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.route_request import RouteRequest, calculated_routes
from app.services.valhala import ValhallaService
from app.services.risk_service import RiskService

router = APIRouter(
    prefix="/rota",
    tags=["Rotas"],
)


def decode_valhalla_shape(
    encoded: str,
) -> list[tuple[float, float]]:
    """
    Decodifica a polyline do Valhalla.

    Retorna coordenadas (latitude, longitude).
    Precisão: 6 casas decimais.
    """

    coordinates = []
    index = 0
    latitude = 0
    longitude = 0

    while index < len(encoded):
        values = []

        for _ in range(2):
            result = 0
            shift = 0

            while True:
                if index >= len(encoded):
                    raise ValueError("Polyline incompleta")

                byte = ord(encoded[index]) - 63
                index += 1

                result |= (byte & 0x1F) << shift
                shift += 5

                if byte < 0x20:
                    break

            delta = (
                ~(result >> 1)
                if result & 1
                else result >> 1
            )

            values.append(delta)

        latitude += values[0]
        longitude += values[1]

        coordinates.append(
            (
                latitude / 1_000_000,
                longitude / 1_000_000,
            )
        )

    return coordinates


@router.post("/{route_request_id}/calculate")
async def calculate_route(
    route_request_id: int,
    session: AsyncSession = Depends(get_session),
):
    # 1. Busca a solicitação no banco.
    result = await session.execute(
        select(
            RouteRequest.id,
            func.ST_Y(RouteRequest.origin).label("origin_lat"),
            func.ST_X(RouteRequest.origin).label("origin_lon"),
            func.ST_Y(RouteRequest.destination).label("destination_lat"),
            func.ST_X(RouteRequest.destination).label("destination_lon"),
            RouteRequest.transport_mode,
        ).where(
            RouteRequest.id == route_request_id
        )
    )

    route_request = result.one_or_none()

    if route_request is None:
        raise HTTPException(
            status_code=404,
            detail="Solicitação de rota não encontrada",
        )

    # 2. Converte o Enum para string.
    transport_mode = route_request.transport_mode

    costing = (
        transport_mode.value
        if transport_mode is not None
        else "auto"
    )

    # 3. Consulta o Valhalla.
    valhalla = ValhallaService()

    try:
        data = await valhalla.calculate_route(
            origin_lat=route_request.origin_lat,
            origin_lon=route_request.origin_lon,
            destination_lat=route_request.destination_lat,
            destination_lon=route_request.destination_lon,
            costing=costing,
        )

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Erro ao consultar o serviço Valhalla",
        ) from exc

    # 4. Valida a resposta.
    trip = data.get("trip")

    if not trip or not trip.get("summary"):
        raise HTTPException(
            status_code=502,
            detail="Resposta inválida do Valhalla",
        )

    summary = trip["summary"]
    legs = trip.get("legs", [])

    if not legs:
        raise HTTPException(
            status_code=502,
            detail="Segmentos da rota não encontrados",
        )

    # 5. Decodifica as geometrias dos segmentos.
    coordinates = []

    try:
        for leg in legs:
            shape = leg.get("shape")

            if not shape:
                continue

            leg_coordinates = decode_valhalla_shape(shape)

            # Evita duplicar o ponto de ligação entre segmentos.
            if (
                coordinates
                and leg_coordinates
                and coordinates[-1] == leg_coordinates[0]
            ):
                leg_coordinates = leg_coordinates[1:]

            coordinates.extend(leg_coordinates)

    except (ValueError, IndexError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível decodificar a geometria da rota",
        ) from exc

    if len(coordinates) < 2:
        raise HTTPException(
            status_code=502,
            detail="A geometria da rota possui pontos insuficientes",
        )

    # 6. Converte latitude/longitude para longitude/latitude.
    wkt_coordinates = ", ".join(
        f"{lon} {lat}"
        for lat, lon in coordinates
    )

    route_geometry = WKTElement(
        f"LINESTRING({wkt_coordinates})",
        srid=4326,
    )

    # 7. Cria o registro da rota calculada.
    calculated_route = calculated_routes(
        route_request_id=route_request.id,
        geometry=route_geometry,
        distance_km=summary["length"],
        duration_seconds=round(summary["time"]),
    )

    session.add(calculated_route)

    # 8. Persiste no PostgreSQL.
    try:
        await session.commit()
        await session.refresh(calculated_route)

    except Exception:
        await session.rollback()
        raise

    # 9. Calcula o risco da rota.
    try:
        risk = await RiskService.calculate(
        session=session,
        route_request_id=route_request.id,
    )

        risk_status = {
            "success": True,
            "code": "RISK_CALCULATED",
            "message": "Risco de criminalidade calculado com sucesso.",
        }

    except Exception as exc:
        await session.rollback()

        print(
            f"ERRO AO CALCULAR RISCO: "
            f"{type(exc).__name__}: {exc}"
    )

    risk = None
    print (risk)
    risk_status = {
        "success": False,
        "code": "RISK_CALCULATION_ERROR",
        "message": (
            "A rota foi calculada, mas não foi possível "
            "calcular o risco de criminalidade."
        ),
    }

# 10. Retorna os resultados para o frontend.
    geometry_geojson = {
    "type": "LineString",
    "coordinates": [
        [lon, lat]
        for lat, lon in coordinates
    ],
  }
    return {
    "success": True,
    "route": {
        "route_request_id": route_request.id,
        "calculated_route_id": calculated_route.id,
        "transport_mode": costing,
        "distance_km": calculated_route.distance_km,
        "duration_seconds": calculated_route.duration_seconds,
        "geometry_points": len(coordinates),
    },
    "risk": {
        "status": risk_status,
        "result": risk,
    },
    "message": "Rota calculada com sucesso.",
}















































































































































































































































































































































































































































