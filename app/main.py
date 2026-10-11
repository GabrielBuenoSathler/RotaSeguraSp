from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.route_request import RouteRequest
from app.schema import RouteRequestCreate

from geoalchemy2.elements import WKTElement
from app.routers.router_requests_v import router as route_requests_router
from fastapi import FastAPI

from app.routers.router_requests_v import router as route_requests_router
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(
    prefix="/rota",
    tags=["Rotas"],
)

app = FastAPI(title="RotaSegura")

app.include_router(route_requests_router)
router = APIRouter(prefix="/rota", tags=["Rotas"])



from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement

from app.core.database import get_session
from app.models.route_request import RouteRequest
from fastapi import FastAPI

from app.routers.router_requests_v import router as route_requests_router




@app.post("/rota/", status_code=201)
async def create_route(
    route: RouteRequestCreate,
    session: AsyncSession = Depends(get_session),
):
    db_route = RouteRequest(
        origin=WKTElement(
            f"POINT({route.origin_lon} {route.origin_lat})",
            srid=4326,
        ),
        destination=WKTElement(
            f"POINT({route.destination_lon} {route.destination_lat})",
            srid=4326,
        ),
        transport_mode=route.transport_mode,
    
    )

    session.add(db_route)

    try:
        await session.commit()
        await session.refresh(db_route)
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao cadastrar a rota.",
        )

    return {
        "id": db_route.id,
        "created_at": db_route.created_at,
        "message": "Rota cadastrada com sucesso",
    }




    session.add(db_route)

    await session.commit()
    await session.refresh(db_route)

    return {
        "id": db_route.id,
        "created_at": db_route.created_at,
        "message": "Rota cadastrada com sucesso",
        }
