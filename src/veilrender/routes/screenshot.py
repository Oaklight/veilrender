"""Screenshot endpoint."""

from __future__ import annotations

import logging

from veilrender._vendor.httpserver import App, Request, Response
from veilrender.auth import verify_token
from veilrender.browser import browser_manager
from veilrender.config import settings
from veilrender.models import ScreenshotRequest

logger = logging.getLogger(__name__)


def register(app: App) -> None:
    """Register screenshot routes on the app."""

    @app.post("/screenshot")
    async def screenshot(request: Request) -> Response:
        verify_token(request)

        try:
            data = request.json()
        except Exception:
            return Response(
                body=b'{"error": "Invalid JSON body"}',
                status_code=400,
                content_type="application/json",
            )

        if "url" not in data:
            return Response(
                body=b'{"error": "Missing \'url\' field"}',
                status_code=400,
                content_type="application/json",
            )

        req = ScreenshotRequest.from_dict(data)
        timeout = req.timeout or settings.timeout

        try:
            async with browser_manager.get_page(
                viewport_width=req.viewport_width,
                viewport_height=req.viewport_height,
            ) as (ctx, page):
                await page.goto(
                    req.url,
                    wait_until=req.wait_until,
                    timeout=timeout,
                )
                png_bytes = await page.screenshot(full_page=req.full_page)
        except Exception as exc:
            logger.error("Screenshot failed for %s: %s", req.url, exc)
            return Response(
                body=f'{{"error": "Screenshot failed: {exc!s}"}}'.encode(),
                status_code=502,
                content_type="application/json",
            )

        return Response(
            body=png_bytes,
            status_code=200,
            content_type="image/png",
        )
