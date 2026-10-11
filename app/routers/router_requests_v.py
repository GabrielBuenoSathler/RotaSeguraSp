import httpx

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.route_request import RouteRequest
from app.services.valhala import ValhallaService
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(
    prefix="/rota",
    tags=["Rotas"],
)
@router.post("/{route_request_id}/calculate")
async def calculate_route(
    route_request_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(
            RouteRequest.id,
            func.ST_Y(RouteRequest.origin).label("origin_lat"),
            func.ST_X(RouteRequest.origin).label("origin_lon"),
            func.ST_Y(RouteRequest.destination).label("destination_lat"),
            func.ST_X(RouteRequest.destination).label("destination_lon"),
            RouteRequest.transport_mode,
        ).where(RouteRequest.id == route_request_id)
    )

    route_request = result.one_or_none()

    if route_request is None:
        raise HTTPException(
            status_code=404,
            detail="Solicitação de rota não encontrada",
        )

    valhalla = ValhallaService()

    try:
        data = await valhalla.calculate_route(
            origin_lat=route_request.origin_lat,
            origin_lon=route_request.origin_lon,
            destination_lat=route_request.destination_lat,
            destination_lon=route_request.destination_lon,
            costing="auto",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Erro ao consultar o serviço Valhalla",
        ) from exc

    trip = data.get("trip")

    if not trip or not trip.get("summary"):
        raise HTTPException(
            status_code=502,
            detail="Resposta inválida do Valhalla",
        )

    return {
        "route_request_id": route_request.id,
        "summary": trip["summary"],
        "route": data,
    }
