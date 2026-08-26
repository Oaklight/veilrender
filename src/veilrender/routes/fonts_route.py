"""Font file serving endpoint — GET /fonts/<filename>.

Serves font files from local directories. If a known font is requested
but not present locally, it is downloaded on-demand from CDN and cached
permanently in ``~/.fonts/`` for future requests.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

from veilrender._vendor.httpserver import App, Request, Response
from veilrender.config import settings
from veilrender.fonts import FONT_REGISTRY

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

_KNOWN_FONTS: dict[str, str] = {
    "NotoColorEmoji.ttf": FONT_REGISTRY["noto-color-emoji"],
    "noto-sans-sc.ttf": FONT_REGISTRY["noto-sans-sc"],
    "noto-sans-tc.ttf": FONT_REGISTRY["noto-sans-tc"],
    "noto-sans-jp.ttf": FONT_REGISTRY["noto-sans-jp"],
    "noto-sans-kr.ttf": FONT_REGISTRY["noto-sans-kr"],
}


def _find_font(filename: str) -> Path | None:
    """Search font directories for a file by name."""
    font_dir = Path(settings.font_dir)
    for search_dir in [font_dir, *_FONT_DIRS]:
        for path in search_dir.rglob(filename):
            if path.is_file():
                return path
    return None


def _download_font(filename: str) -> Path | None:
    """Download a known font on-demand, cache in font_dir."""
    url = _KNOWN_FONTS.get(filename)
    if not url:
        return None

    if settings.font_mirror:
        url = f"{settings.font_mirror}/{url}"

    font_dir = Path(settings.font_dir)
    font_dir.mkdir(parents=True, exist_ok=True)
    dest = font_dir / filename

    logger.info("On-demand font download: %s", filename)
    try:
        resp = urllib.request.urlopen(url, timeout=60)
        dest.write_bytes(resp.read())
        return dest
    except Exception:
        logger.warning("Failed to download font %s", filename, exc_info=True)
        return None


def register(app: App) -> None:
    """Register font serving route on the app."""

    @app.get("/fonts/{filename}")
    async def serve_font(request: Request) -> Response:
        filename = request.path_params.get("filename", "")
        if not filename or "/" in filename or "\\" in filename:
            return Response(
                body=b'{"error": "Invalid filename"}',
                status_code=400,
                content_type="application/json",
            )

        path = _find_font(filename)

        if path is None:
            path = _download_font(filename)

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
