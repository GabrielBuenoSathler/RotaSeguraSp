from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.route_request import RouteRequest
from app.schema import RouteRequestCreate

from geoalchemy2.elements import WKTElement

app = FastAPI()


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
    )

    session.add(db_route)

    await session.commit()
    await session.refresh(db_route)

    return {
        "id": db_route.id,
        "created_at": db_route.created_at,
        "message": "Rota cadastrada com sucesso",
    }
