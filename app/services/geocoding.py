import httpx
from pydantic import BaseModel, Field, TypeAdapter

from app.core.config import settings


class GeocodingUnavailableError(RuntimeError):
    pass


class Place(BaseModel):
    display_name: str
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)


class GeocodingService:
    @staticmethod
    async def search(query: str) -> list[Place]:
        if not settings.nominatim_url:
            raise GeocodingUnavailableError("Busca por endereço não configurada")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{settings.nominatim_url.rstrip('/')}/search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": 5,
                    "countrycodes": "br",
                    "accept-language": "pt-BR",
                },
                headers={"User-Agent": settings.geocoder_user_agent},
            )
            response.raise_for_status()
            return TypeAdapter(list[Place]).validate_python(response.json())[:5]
