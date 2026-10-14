from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.routers.places import router as places_router
from app.routers.router_requests_v import router as route_requests_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="RotaSegura", lifespan=lifespan)
app.include_router(route_requests_router)
app.include_router(places_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
