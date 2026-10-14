import httpx

from app.core.config import settings


class ValhallaService:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.valhalla_url).rstrip("/")

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        costing: str = "auto",
        alternates: int = 0,
    ) -> dict:

        payload = {
            "locations": [
                {
                    "lat": origin_lat,
                    "lon": origin_lon,
                },
                {
                    "lat": destination_lat,
                    "lon": destination_lon,
                },
            ],
            "costing": costing,
            "units": "kilometers",
        }
        if alternates:
            payload["alternates"] = alternates

        async with httpx.AsyncClient(
            timeout=settings.valhalla_timeout_seconds
        ) as client:
            response = await client.post(
                f"{self.base_url}/route",
                json=payload,
            )

            response.raise_for_status()

            return response.json()
