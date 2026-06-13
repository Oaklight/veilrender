"""Health check endpoint."""

from __future__ import annotations

from veilrender._vendor.httpserver import App, JSONResponse, Request


def register(app: App) -> None:
    """Register health check routes on the app."""

    @app.get("/health")
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})
