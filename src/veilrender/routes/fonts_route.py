"""Font file serving endpoint — GET /fonts/<filename>.

Serves font files from local directories. If a known font is requested
but not present locally, it is downloaded on-demand from CDN and cached
permanently in ``~/.fonts/`` for future requests.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import urllib.request
from pathlib import Path

from veilrender._vendor.httpserver import App, Request, Response
from veilrender.config import settings
from veilrender.fonts import FONT_REGISTRY, _resolve_github_font_url

logger = logging.getLogger(__name__)

_FONT_DIRS = [
    Path("/usr/share/fonts"),
    Path("/usr/local/share/fonts"),
]

_MIME_TYPES = {
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}

_KNOWN_FONT_KEYS = [
    "noto-color-emoji",
    "noto-sans-sc",
    "noto-sans-tc",
    "noto-sans-jp",
    "noto-sans-kr",
]

_FONTSOURCE_BASE = "https://cdn.jsdelivr.net/npm/@fontsource"
_FONTSOURCE_CACHE = Path(settings.font_dir) / "fontsource"


def _find_font(filename: str) -> Path | None:
    """Search font directories for a file by name."""
    font_dir = Path(settings.font_dir)
    for search_dir in [font_dir, *_FONT_DIRS]:
        if not search_dir.exists():
            continue
        candidate = search_dir / filename
        if candidate.is_file():
            return candidate
        for path in search_dir.iterdir():
            if path.is_dir():
                candidate = path / filename
                if candidate.is_file():
                    return candidate
    return None


def _download_font(filename: str) -> Path | None:
    """Download a known font on-demand, cache in font_dir."""
    resolved_url: str | None = None
    for key in _KNOWN_FONT_KEYS:
        spec = FONT_REGISTRY[key]
        resolved_name, resolved = _resolve_github_font_url(key, spec)
        if resolved_name == filename:
            resolved_url = resolved
            break

    if not resolved_url:
        return None

    if settings.font_mirror:
        resolved_url = f"{settings.font_mirror}/{resolved_url}"

    font_dir = Path(settings.font_dir)
    font_dir.mkdir(parents=True, exist_ok=True)
    dest = font_dir / filename

    if dest.exists():
        return dest

    logger.info("On-demand font download: %s", filename)
    try:
        resp = urllib.request.urlopen(resolved_url, timeout=60)
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(resp.read())
        tmp.rename(dest)
        try:
            subprocess.run(
                ["fc-cache", "-f", str(font_dir)], capture_output=True, timeout=10
            )
        except Exception:
            pass
        return dest
    except Exception:
        logger.warning("Failed to download font %s", filename, exc_info=True)
        return None


def _download_fontsource_file(font_name: str, filename: str) -> Path | None:
    """Download a fontsource woff2/woff file on-demand, cache locally."""
    cache_dir = _FONTSOURCE_CACHE / font_name
    dest = cache_dir / filename
    if dest.exists():
        return dest

    url = f"{_FONTSOURCE_BASE}/{font_name}/files/{filename}"
    if settings.font_mirror:
        url = f"{settings.font_mirror}/{url}"

    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info("On-demand fontsource download: %s/%s", font_name, filename)
    try:
        resp = urllib.request.urlopen(url, timeout=30)
        tmp = dest.with_suffix(".tmp")
        tmp.write_bytes(resp.read())
        tmp.rename(dest)
        return dest
    except Exception:
        logger.warning(
            "Failed to download fontsource %s/%s", font_name, filename, exc_info=True
        )
        return None


def register(app: App) -> None:
    """Register font serving routes on the app."""

    @app.get("/fonts/fontsource/<path:rest>")
    async def serve_fontsource(request: Request, rest: str = "") -> Response:
        parts = rest.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return Response(
                body=b'{"error": "Invalid path"}',
                status_code=400,
                content_type="application/json",
            )
        font_name, filename = parts
        if ".." in filename or "/" in filename:
            return Response(
                body=b'{"error": "Invalid filename"}',
                status_code=400,
                content_type="application/json",
            )

        cached = _FONTSOURCE_CACHE / font_name / filename
        if not cached.exists():
            cached_path = await asyncio.to_thread(
                _download_fontsource_file, font_name, filename
            )
            if cached_path is None:
                return Response(
                    body=b'{"error": "Font file not found"}',
                    status_code=404,
                    content_type="application/json",
                )
            cached = cached_path

        suffix = cached.suffix.lower()
        content_type = _MIME_TYPES.get(suffix, "application/octet-stream")
        return Response(
            body=cached.read_bytes(),
            status_code=200,
            content_type=content_type,
            headers={
                "Cache-Control": "public, max-age=604800",
                "Access-Control-Allow-Origin": "*",
            },
        )

    @app.get("/fonts/<path:filename>")
    async def serve_font(request: Request, filename: str = "") -> Response:
        if not filename or "/" in filename or "\\" in filename:
            return Response(
                body=b'{"error": "Invalid filename"}',
                status_code=400,
                content_type="application/json",
            )

        path = _find_font(filename)

        if path is None:
            path = await asyncio.to_thread(_download_font, filename)

        if path is None:
            return Response(
                body=b'{"error": "Font not found"}',
                status_code=404,
                content_type="application/json",
            )

        suffix = path.suffix.lower()
        content_type = _MIME_TYPES.get(suffix, "application/octet-stream")

        return Response(
            body=path.read_bytes(),
            status_code=200,
            content_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*",
            },
        )
