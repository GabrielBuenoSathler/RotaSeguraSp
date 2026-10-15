import asyncio

import httpx
import pytest
from fastapi import FastAPI

from app.core.security import ResourceLimitsMiddleware


def make_app():
    app = FastAPI()
    app.add_middleware(ResourceLimitsMiddleware)
    return app


@pytest.mark.asyncio
async def test_calculation_rate_limit_and_health_bypass():
    app = make_app()

    @app.post("/rota/{route_id}/calculate")
    async def calculate(route_id: int):
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for _ in range(10):
            assert (await client.post("/rota/1/calculate")).status_code == 200
        response = await client.post("/rota/1/calculate")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
        assert (await client.get("/health")).status_code == 200


@pytest.mark.asyncio
async def test_concurrency_limit_and_release():
    app = make_app()
    entered = asyncio.Queue()
    release = asyncio.Event()

    @app.get("/places")
    async def places():
        await entered.put(True)
        await release.wait()
        return {"ok": True}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        pending = [asyncio.create_task(client.get("/places")) for _ in range(4)]
        for _ in range(4):
            await asyncio.wait_for(entered.get(), 2)
        assert (await client.get("/places")).status_code == 429
        release.set()
        assert all(
            response.status_code == 200 for response in await asyncio.gather(*pending)
        )
        assert (await client.get("/places")).status_code == 200


@pytest.mark.asyncio
async def test_general_quota_ignores_spoofed_forwarding_headers():
    app = make_app()

    @app.get("/places")
    async def places():
        return {"ok": True}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for i in range(60):
            response = await client.get(
                "/places", headers={"X-Forwarded-For": f"192.0.2.{i}"}
            )
            assert response.status_code == 200
        assert (await client.get("/places")).status_code == 429


@pytest.mark.asyncio
async def test_handler_exception_releases_concurrency_slot():
    app = make_app()

    @app.get("/places")
    async def places():
        raise RuntimeError("provider failure")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        for _ in range(6):
            assert (await client.get("/places")).status_code == 500
