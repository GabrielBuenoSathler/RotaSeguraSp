import asyncio
from collections import OrderedDict
from time import monotonic

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
    _lock = asyncio.Lock()
    _last_request = 0.0
    _cache: OrderedDict = OrderedDict()

    @classmethod
    async def _request(cls, endpoint: str, params: dict):
        if not settings.nominatim_url:
            raise GeocodingUnavailableError("Busca por endereço não configurada")
        url = f"{settings.nominatim_url.rstrip('/')}/{endpoint}"
        key = (url, tuple(sorted(params.items())))
        async with cls._lock:
            cached = cls._cache.get(key)
            if cached and monotonic() - cached[0] < 3600:
                cls._cache.move_to_end(key)
                return cached[1]
            # Serialize lookups and respect the public provider's one-request/second limit.
            await asyncio.sleep(max(0, 1.05 - (monotonic() - cls._last_request)))
            cls._last_request = monotonic()
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    url,
                    params={"format": "jsonv2", "accept-language": "pt-BR", **params},
                    headers={"User-Agent": settings.geocoder_user_agent},
                )
                response.raise_for_status()
                data = response.json()
            cls._cache[key] = (monotonic(), data)
            if len(cls._cache) > 512:
                cls._cache.popitem(last=False)
            return data

    @classmethod
    async def search(cls, query: str) -> list[Place]:
        data = await cls._request(
            "search", {"q": query, "limit": 5, "countrycodes": "br"}
        )
        return TypeAdapter(list[Place]).validate_python(data)[:5]

    @classmethod
    async def reverse(cls, lat: float, lon: float) -> Place | None:
        data = await cls._request(
            "reverse", {"lat": lat, "lon": lon, "zoom": 18, "addressdetails": 1}
        )
        if not isinstance(data, dict):
            raise ValueError("Resposta de endereço inválida")
        if data.get("error"):
            return None
        address = data.get("address") or {}
        street = next(
            (
                address[key]
                for key in ("road", "pedestrian", "residential", "footway", "path")
                if address.get(key)
            ),
            None,
        )
        city = address.get("city") or address.get("town") or address.get("municipality")
        if street:
            name = ", ".join(
                str(part)
                for part in (
                    street,
                    address.get("house_number"),
                    address.get("suburb"),
                    city,
                )
                if part
            )
        else:
            name = data.get("display_name")
        if not name:
            return None
        return Place(display_name=name, lat=lat, lon=lon)
