import hashlib
import logging
import secrets
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Path
from geoalchemy2.elements import WKTElement
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.route_request import CalculatedRoute, RouteRequest
from app.schema import (
    CalculateResponse,
    RouteRequestCreate,
    RouteRequestResponse,
    ValhallaTrip,
)
from app.services.risk_service import RiskService
from app.services.valhala import ValhallaService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rota", tags=["Rotas"])
Session = Annotated[AsyncSession, Depends(get_session)]


def decode_valhalla_shape(encoded: str) -> list[tuple[float, float]]:
    """Decode polyline6 into latitude/longitude pairs, rejecting invalid shapes."""
    coordinates = []
    index = latitude = longitude = 0
    while index < len(encoded):
        values = []
        for _ in range(2):
            result = shift = 0
            while True:
                if index >= len(encoded) or shift > 30:
                    raise ValueError("Polyline incompleta ou inválida")
                byte = ord(encoded[index]) - 63
                index += 1
                if not 0 <= byte <= 63:
                    raise ValueError("Caractere inválido na polyline")
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            values.append(~(result >> 1) if result & 1 else result >> 1)
        latitude += values[0]
        longitude += values[1]
        point = (latitude / 1_000_000, longitude / 1_000_000)
        if not (-90 <= point[0] <= 90 and -180 <= point[1] <= 180):
            raise ValueError("Coordenadas inválidas na polyline")
        coordinates.append(point)
    return coordinates


def parse_trip(data: dict) -> tuple[ValhallaTrip, list[tuple[float, float]]]:
    trip = ValhallaTrip.model_validate(data)
    coordinates = []
    for leg in trip.legs:
        points = decode_valhalla_shape(leg.shape)
        if coordinates and points and coordinates[-1] == points[0]:
            points = points[1:]
        coordinates.extend(points)
        if len(coordinates) > 20000:
            raise ValueError("Geometria excede o limite de pontos")
    if len(coordinates) < 2:
        raise ValueError("A geometria da rota possui pontos insuficientes")
    return trip, coordinates


@router.post("/", status_code=201, response_model=RouteRequestResponse)
async def create_route(route: RouteRequestCreate, session: Session):
    token = secrets.token_urlsafe(32)
    db_route = RouteRequest(
        access_token_hash=hashlib.sha256(token.encode()).hexdigest(),
        origin=WKTElement(f"POINT({route.origin_lon} {route.origin_lat})", srid=4326),
        destination=WKTElement(
            f"POINT({route.destination_lon} {route.destination_lat})", srid=4326
        ),
        transport_mode=route.transport_mode,
    )
    session.add(db_route)
    try:
        await session.commit()
        await session.refresh(db_route)
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.exception("Erro ao cadastrar solicitação de rota")
        raise HTTPException(500, "Erro ao cadastrar a rota.") from exc
    return {
        "access_token": token,
        "id": db_route.id,
        "created_at": db_route.created_at,
        "message": "Rota cadastrada com sucesso",
    }


@router.post("/{route_request_id}/calculate", response_model=CalculateResponse)
async def calculate_route(
    route_request_id: Annotated[int, Path(gt=0)],
    session: Session,
    authorization: Annotated[str | None, Header(max_length=100)] = None,
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(404, "Solicitação de rota não encontrada")
    token_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
    result = await session.execute(
        select(
            RouteRequest.id,
            func.ST_Y(RouteRequest.origin).label("origin_lat"),
            func.ST_X(RouteRequest.origin).label("origin_lon"),
            func.ST_Y(RouteRequest.destination).label("destination_lat"),
            func.ST_X(RouteRequest.destination).label("destination_lon"),
            RouteRequest.transport_mode,
        ).where(
            RouteRequest.id == route_request_id,
            RouteRequest.access_token_hash == token_hash,
        )
    )
    request = result.one_or_none()
    if request is None:
        raise HTTPException(404, "Solicitação de rota não encontrada")
    costing = request.transport_mode.value
    try:
        data = await ValhallaService().calculate_route(
            origin_lat=request.origin_lat,
            origin_lon=request.origin_lon,
            destination_lat=request.destination_lat,
            destination_lon=request.destination_lon,
            costing=costing,
            alternates=settings.route_alternates,
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            504, "O serviço de rotas excedeu o tempo de resposta"
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Erro ao consultar o serviço Valhalla") from exc

    try:
        main = parse_trip(data["trip"])
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise HTTPException(502, "Resposta inválida do Valhalla") from exc
    parsed = [main]
    alternates = data.get("alternates", [])
    if isinstance(alternates, list):
        for alternate in alternates[: settings.route_alternates]:
            try:
                candidate = parse_trip(alternate["trip"])
            except (KeyError, TypeError, ValueError, ValidationError):
                logger.warning("Alternativa inválida recebida do Valhalla")
                continue
            if all(candidate[1] != item[1] for item in parsed):
                parsed.append(candidate)

    records = []
    for trip, coordinates in parsed:
        points = ", ".join(f"{lon} {lat}" for lat, lon in coordinates)
        record = CalculatedRoute(
            route_request_id=route_request_id,
            geometry=WKTElement(f"LINESTRING({points})", srid=4326),
            distance_km=trip.summary.length,
            duration_seconds=round(trip.summary.time),
        )
        session.add(record)
        records.append(record)
    try:
        await session.flush()
        # Snapshot all attributes before any risk query can roll back.
        routes = [
            {
                "route_request_id": route_request_id,
                "calculated_route_id": record.id,
                "transport_mode": costing,
                "distance_km": record.distance_km,
                "duration_seconds": record.duration_seconds,
                "geometry_points": len(coordinates),
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lat, lon in coordinates],
                },
            }
            for record, (_, coordinates) in zip(records, parsed, strict=True)
        ]
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.exception("Erro ao persistir rotas da solicitação %s", route_request_id)
        raise HTTPException(500, "Erro ao salvar a rota calculada.") from exc

    options = []
    for route in routes:
        try:
            risk = await RiskService.calculate(session, route["calculated_route_id"])
            status = {
                "success": True,
                "code": "RISK_CALCULATED",
                "message": "Exposição a ocorrências calculada com sucesso.",
            }
        except (SQLAlchemyError, ValueError) as exc:
            await session.rollback()
            logger.exception(
                "Erro ao calcular risco da rota %s: %s",
                route["calculated_route_id"],
                type(exc).__name__,
            )
            risk = None
            status = {
                "success": False,
                "code": "RISK_CALCULATION_ERROR",
                "message": "A rota foi calculada, mas a análise de ocorrências está indisponível.",
            }
        options.append({"route": route, "risk": {"status": status, "result": risk}})
    return {
        "success": True,
        **options[0],
        "alternatives": options[1:],
        "message": "Rota calculada com sucesso.",
    }
