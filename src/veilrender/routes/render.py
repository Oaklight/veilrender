"""Page rendering endpoint."""

from __future__ import annotations

import logging
import re
import time

from veilrender._vendor.httpserver import App, JSONResponse, Request
from veilrender._vendor.readability import extract as readability_extract
from veilrender._vendor.soup import Soup
from veilrender import stats
from veilrender.auth import verify_token
from veilrender.browser import browser_manager
from veilrender.config import settings
from veilrender.models import (
    LinkInfo,
    PageMetadata,
    RenderContent,
    RenderRequest,
    RenderResponse,
)
from veilrender.storage import storage_manager

logger = logging.getLogger(__name__)


def _extract_links(html: str, base_url: str) -> list[LinkInfo]:
    """Extract links from HTML using zerodep soup."""
    links: list[LinkInfo] = []
    try:
        soup = Soup(html)
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if href and not href.startswith(("#", "javascript:")):
                links.append(LinkInfo(url=href, text=text))
    except Exception:
        logger.debug("Failed to extract links", exc_info=True)
    return links


def _html_to_markdown(html: str) -> str:
    """Simple HTML to Markdown conversion using readability text output.

    This is a lightweight conversion: we extract readable content and
    return the plain-text representation, which is sufficient for LLM
    consumption. For full-fidelity HTML→Markdown, a dedicated converter
    (like markdownify) would be needed.
    """
    try:
        result = readability_extract(html)
        return result.text
    except Exception:
        # Fallback: strip tags and return raw text
        return re.sub(r"<[^>]+>", "", html)


def register(app: App) -> None:
    """Register render routes on the app."""

    @app.post("/render")
    async def render(request: Request) -> JSONResponse:
        verify_token(request)

        try:
            data = request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

        if "url" not in data:
            return JSONResponse({"error": "Missing 'url' field"}, status_code=400)

        req = RenderRequest.from_dict(data)
        timeout = req.timeout or settings.timeout
        stats.render.requests += 1
        t0 = time.monotonic()

        # Check cache before rendering
        cache_key: str | None = None
        if storage_manager.enabled:
            cache_key = storage_manager.make_key(req.url, req.formats, req.wait_until)
            cached = await storage_manager.get(cache_key)
            if cached is not None:
                elapsed = (time.monotonic() - t0) * 1000
                stats.render.cache_hits += 1
                stats.render.record_success(elapsed)
                return JSONResponse(cached)
            stats.render.cache_misses += 1

        try:
            async with browser_manager.get_page() as (ctx, page):
                response = await page.goto(
                    req.url,
                    wait_until=req.wait_until,
                    timeout=timeout,
                )
                status_code = response.status if response else 0
                title = await page.title()
                final_url = page.url
                html = await page.content()
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            stats.render.record_failure(elapsed)
            logger.error("Render failed for %s: %s", req.url, exc)
            return JSONResponse(
                {"error": f"Render failed: {exc!s}"},
                status_code=502,
            )

        # Build content based on requested formats
        content = RenderContent()

        if "html" in req.formats:
            content.html = html

        if "readability" in req.formats:
            try:
                rd = readability_extract(html, url=final_url)
                content.readability = rd.text
            except Exception:
                logger.debug("Readability extraction failed", exc_info=True)
                content.readability = None

        if "markdown" in req.formats:
            content.markdown = _html_to_markdown(html)

        # Extract links
        links = _extract_links(html, final_url)

        result = RenderResponse(
            content=content,
            metadata=PageMetadata(
                title=title,
                url=final_url,
                status_code=status_code,
            ),
            links=links,
        )

        elapsed = (time.monotonic() - t0) * 1000
        stats.render.record_success(elapsed)

        # Store to cache
        result_dict = result.to_dict()
        if cache_key is not None:
            try:
                await storage_manager.put(cache_key, result_dict)
            except Exception:
                logger.debug("Cache store failed", exc_info=True)

        return JSONResponse(result_dict)
