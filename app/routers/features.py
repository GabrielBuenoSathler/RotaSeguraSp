from fastapi import APIRouter, Response

from app.core.config import settings

router = APIRouter(tags=["Configuração pública"])


@router.get("/features", response_model=dict[str, bool])
async def features(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {
        "geocoding": settings.feature_geocoding and bool(settings.nominatim_url),
        "route_alternatives": (
            settings.feature_route_alternatives and settings.route_alternates > 0
        ),
    }
