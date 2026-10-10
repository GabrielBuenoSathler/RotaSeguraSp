import httpx


class ValhallaService:

    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        costing: str = "auto",
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/route",
                json=payload,
            )

            response.raise_for_status()

            return response.json()
