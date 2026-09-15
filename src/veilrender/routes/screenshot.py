"""Screenshot endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from veilrender._vendor.httpserver import App, Request, Response
from veilrender import stats
from veilrender.auth import verify_token
from veilrender.browser import browser_manager
from veilrender.config import settings
from veilrender.fonts import get_auto_font_css_urls, get_emoji_font_css
from veilrender.models import ScreenshotRequest
from veilrender.url_validator import URLValidationError, validate_url

logger = logging.getLogger(__name__)

_CONTENT_TYPES: dict[str, str] = {
    "png": "image/png",
    "jpeg": "image/jpeg",
}


def register(app: App) -> None:
    """Register screenshot routes on the app."""

    @app.post("/screenshot")
    async def screenshot(request: Request) -> Response:
        verify_token(request)

        try:
            data = request.json()
        except Exception:
            return Response(
                body=json.dumps({"error": "Invalid JSON body"}).encode(),
                status_code=400,
                content_type="application/json",
            )

        if "url" not in data:
            return Response(
                body=json.dumps({"error": "Missing 'url' field"}).encode(),
                status_code=400,
                content_type="application/json",
            )

        try:
            req = ScreenshotRequest.from_dict(data)
            req.validate()
        except ValueError as exc:
            return Response(
                body=json.dumps({"error": str(exc)}).encode(),
                status_code=400,
                content_type="application/json",
            )

        try:
            validate_url(req.url)
        except URLValidationError as exc:
            return Response(
                body=f'{{"error": "URL rejected: {exc!s}"}}'.encode(),
                status_code=400,
                content_type="application/json",
            )

        timeout = req.timeout or settings.timeout
        stats.screenshot.requests += 1
        t0 = time.monotonic()

        async def _do_screenshot(
            *, min_tier: int = 0, tier_timeout: int | None = None
        ) -> tuple[bytes, str]:
            t = tier_timeout or timeout
            async with browser_manager.get_page(
                viewport_width=req.viewport_width,
                viewport_height=req.viewport_height,
                device_scale_factor=req.scale,
                color_scheme=req.color_scheme,
                min_tier=min_tier,
            ) as (ctx, page, engine, force_wu):
                effective_wu = force_wu or req.wait_until
                await page.goto(
                    req.url,
                    wait_until=effective_wu,
                    timeout=t,
                )
                css_urls = [req.font_css] if req.font_css else get_auto_font_css_urls()
                host = request.headers.get("host", "")
                proto = request.headers.get("x-forwarded-proto", "")
                emoji_css = get_emoji_font_css(host, proto)
                for css_url in css_urls:
                    await page.add_style_tag(url=css_url)
                if emoji_css:
                    await page.add_style_tag(content=emoji_css)
                if css_urls or emoji_css:
                    await page.evaluate("() => document.fonts.ready")

                if req.wait_for:
                    elapsed_ms = (time.monotonic() - t0) * 1000
                    remaining = max(timeout - elapsed_ms, 0)
                    await page.wait_for_selector(req.wait_for, timeout=remaining)

                screenshot_kwargs: dict[str, Any] = {
                    "full_page": req.full_page,
                }
                if req.format == "jpeg":
                    screenshot_kwargs["type"] = "jpeg"
                    if req.quality is not None:
                        screenshot_kwargs["quality"] = req.quality
                if req.transparent:
                    screenshot_kwargs["omit_background"] = True
                if req.clip:
                    screenshot_kwargs["clip"] = {
                        "x": req.clip.x,
                        "y": req.clip.y,
                        "width": req.clip.width,
                        "height": req.clip.height,
                    }

                if req.selector:
                    locator = page.locator(req.selector)
                    element_kwargs = {
                        k: v for k, v in screenshot_kwargs.items() if k != "full_page"
                    }
                    return await locator.screenshot(**element_kwargs), engine
                return await page.screenshot(**screenshot_kwargs), engine

        try:
            if browser_manager.has_fallback_tier(0):
                tier0_timeout = min(settings.obscura_timeout, timeout)
                tier0_task = asyncio.create_task(
                    _do_screenshot(tier_timeout=tier0_timeout)
                )
                try:
                    result = await asyncio.wait_for(
                        asyncio.shield(tier0_task),
                        timeout=tier0_timeout / 1000,
                    )
                    image_bytes, engine = result
                except Exception as first_exc:
                    logger.warning(
                        "Tier-0 screenshot slow/failed for %s: %s, racing with tier-1",
                        req.url,
                        type(first_exc).__name__,
                    )
                    tier1_task = asyncio.create_task(_do_screenshot(min_tier=1))
                    if tier0_task.done():
                        image_bytes, engine = await tier1_task
                    else:
                        done, pending = await asyncio.wait(
                            {tier0_task, tier1_task},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for p in pending:
                            p.cancel()
                            try:
                                await p
                            except (asyncio.CancelledError, Exception):
                                pass
                        winner = done.pop()
                        if winner.exception() and pending:
                            winner = (await asyncio.wait(pending))[0].pop()
                        image_bytes, engine = winner.result()
            else:
                image_bytes, engine = await _do_screenshot()
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            stats.screenshot.record_failure(elapsed)
            logger.error("Screenshot failed for %s: %s", req.url, exc)
            return Response(
                body=f'{{"error": "Screenshot failed: {exc!s}"}}'.encode(),
                status_code=502,
                content_type="application/json",
            )

        elapsed = (time.monotonic() - t0) * 1000
        stats.screenshot.record_success(elapsed)
        headers = {}
        if settings.render_engine_header:
            headers["X-Render-Engine"] = engine
        return Response(
            body=image_bytes,
            status_code=200,
            headers=headers or None,
            content_type=_CONTENT_TYPES[req.format],
        )
