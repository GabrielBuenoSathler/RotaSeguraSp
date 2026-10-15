"""Bounded process-wide quotas. Client addresses must come from a trusted proxy."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class ResourceLimitsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.window = -1
        self.clients = {}
        self.total = 0
        self.active = 0

    async def dispatch(self, request, call_next):
        path = request.url.path
        calculate = path.startswith("/rota/") and path.endswith("/calculate")
        protected = calculate or (
            path.rstrip("/") in {"/rota", "/places"} or path.startswith("/places/")
        )
        if not protected:
            return await call_next(request)
        window = int(time.monotonic() // 60)
        if window != self.window:
            self.clients.clear()
            self.total = 0
            self.window = window
        client = request.client.host if request.client else "unknown"
        counts = self.clients.get(client, [0, 0])
        if (
            counts[0] >= 60
            or (calculate and counts[1] >= 10)
            or self.total >= 600
            or (client not in self.clients and len(self.clients) >= 10000)
        ):
            return JSONResponse(
                {"detail": "Limite de requisições atingido. Tente novamente em breve."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        counts[0] += 1
        counts[1] += int(calculate)
        self.clients[client] = counts
        self.total += 1
        if self.active >= 4:
            return JSONResponse(
                {"detail": "Serviço ocupado. Tente novamente em breve."},
                status_code=429,
                headers={"Retry-After": "5"},
            )
        self.active += 1
        try:
            response = await call_next(request)
            if path.startswith("/rota"):
                response.headers["Cache-Control"] = "no-store"
            return response
        finally:
            self.active -= 1
