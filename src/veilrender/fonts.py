"""On-demand font download and auto-detection for screenshot i18n support."""

from __future__ import annotations

import logging
import subprocess
import urllib.request
from pathlib import Path

from veilrender.config import settings

logger = logging.getLogger(__name__)

_JSDELIVR = "https://cdn.jsdelivr.net/gh"

FONT_REGISTRY: dict[str, str] = {
    "noto-sans-sc": f"{_JSDELIVR}/google/fonts@main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
    "noto-sans-tc": f"{_JSDELIVR}/google/fonts@main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf",
    "noto-sans-jp": f"{_JSDELIVR}/google/fonts@main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf",
    "noto-sans-kr": f"{_JSDELIVR}/google/fonts@main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
    "noto-color-emoji": f"{_JSDELIVR}/googlefonts/noto-emoji@main/fonts/NotoColorEmoji.ttf",
    "noto-sans-arabic": f"{_JSDELIVR}/google/fonts@main/ofl/notosansarabic/NotoSansArabic%5Bwght%5D.ttf",
    "noto-sans-thai": f"{_JSDELIVR}/google/fonts@main/ofl/notosansthai/NotoSansThai%5Bwght%5D.ttf",
    "noto-sans-devanagari": f"{_JSDELIVR}/google/fonts@main/ofl/notosansdevanagari/NotoSansDevanagari%5Bwght%5D.ttf",
    "lxgw-wenkai": f"{_JSDELIVR}/lxgw/LxgwWenKai@main/fonts/TTF/LXGWWenKai-Regular.ttf",
}

FONT_ALIASES: dict[str, list[str]] = {
    "cjk": ["noto-sans-sc", "noto-sans-tc", "noto-sans-jp", "noto-sans-kr"],
    "i18n": [
        "noto-sans-sc",
        "noto-sans-tc",
        "noto-sans-jp",
        "noto-sans-kr",
        "noto-color-emoji",
        "noto-sans-arabic",
        "noto-sans-thai",
        "noto-sans-devanagari",
    ],
}


def _resolve_entries(font_specs: list[str]) -> list[tuple[str, str]]:
    """Resolve font specs into (filename, url) pairs."""
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()

    for spec in font_specs:
        if spec in FONT_ALIASES:
            for name in FONT_ALIASES[spec]:
                if name not in seen:
                    seen.add(name)
                    entries.append((f"{name}.ttf", FONT_REGISTRY[name]))
        elif spec in FONT_REGISTRY:
            if spec not in seen:
                seen.add(spec)
                entries.append((f"{spec}.ttf", FONT_REGISTRY[spec]))
        elif spec.startswith(("http://", "https://")):
            filename = spec.rsplit("/", 1)[-1].split("?")[0] or "custom-font.ttf"
            if filename not in seen:
                seen.add(filename)
                entries.append((filename, spec))
        else:
            logger.warning("Unknown font spec: %s", spec)

    return entries


def ensure_fonts(font_specs: list[str]) -> bool:
    """Download fonts that are not already present.

    Returns:
        True if any fonts were downloaded (caller may need to restart browser).
    """
    font_dir = Path(settings.font_dir)
    font_dir.mkdir(parents=True, exist_ok=True)

    entries = _resolve_entries(font_specs)
    if not entries:
        return False

    downloaded = 0
    for filename, url in entries:
        dest = font_dir / filename
        if dest.exists():
            logger.debug("Font already present: %s", dest)
            continue

        # Proxy-style mirror: prefixes the full URL, e.g.
        # VEILRENDER_FONT_MIRROR=https://ghfast.top → ghfast.top/https://cdn.jsdelivr.net/...
        if settings.font_mirror:
            url = f"{settings.font_mirror}/{url}"

        logger.info("Downloading font: %s", filename)
        try:
            resp = urllib.request.urlopen(url, timeout=60)
            dest.write_bytes(resp.read())
            downloaded += 1
        except Exception:
            logger.warning(
                "Failed to download font %s from %s", filename, url, exc_info=True
            )

    if downloaded > 0:
        logger.info("Downloaded %d font(s), updating font cache...", downloaded)
        try:
            subprocess.run(
                ["fc-cache", "-f", str(font_dir)],
                capture_output=True,
                timeout=30,
            )
        except FileNotFoundError:
            logger.debug("fc-cache not found, skipping font cache update")
        except Exception:
            logger.debug("fc-cache failed", exc_info=True)
    else:
        logger.info("All %d font(s) already present", len(entries))
    return downloaded > 0


# ── Auto-detection: probe local fonts, generate CSS for missing ones ─────

# Map fc-list language tags to jsDelivr @fontsource CSS URLs
_FONTSOURCE = "https://cdn.jsdelivr.net/npm/@fontsource"
_LANG_TO_CSS: dict[str, str] = {
    "zh-cn": f"{_FONTSOURCE}/noto-sans-sc/index.css",
    "zh-tw": f"{_FONTSOURCE}/noto-sans-tc/index.css",
    "ja": f"{_FONTSOURCE}/noto-sans-jp/index.css",
    "ko": f"{_FONTSOURCE}/noto-sans-kr/index.css",
    "ar": f"{_FONTSOURCE}/noto-sans-arabic/index.css",
    "th": f"{_FONTSOURCE}/noto-sans-thai/index.css",
    "hi": f"{_FONTSOURCE}/noto-sans-devanagari/index.css",
}

_auto_css_urls: list[str] | None = None
_auto_detected = False
_needs_emoji_serving = False


def _detect_missing_fonts() -> list[str]:
    """Probe local font coverage via fc-list, return CSS URLs for missing scripts."""
    missing: list[str] = []
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{lang}\n"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        installed_langs: set[str] = set()
        for line in result.stdout.lower().splitlines():
            for lang in line.split("|"):
                stripped = lang.strip()
                if stripped:
                    installed_langs.add(stripped)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        installed_langs = set()

    for lang, css_url in _LANG_TO_CSS.items():
        if lang not in installed_langs:
            missing.append(css_url)

    return missing


def has_local_emoji() -> bool:
    """Check if a color emoji font is available locally."""
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{family}\n"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "emoji" in result.stdout.lower()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_auto_font_css_urls() -> list[str]:
    """Return CSS URLs for missing local fonts.

    For CJK/Arabic/Thai/Hindi: jsDelivr @fontsource CSS URLs.
    For emoji: needs gateway font serving (CSS injection doesn't work).

    Result is cached after first call. Override with ``VEILRENDER_FONT_CSS``
    env var (comma-separated URLs) or per-request ``font_css`` parameter.
    """
    global _auto_css_urls, _auto_detected, _needs_emoji_serving

    if _auto_detected:
        return _auto_css_urls or []

    _auto_detected = True

    explicit = settings.font_css
    if explicit:
        _auto_css_urls = [u.strip() for u in explicit.split(",") if u.strip()]
        logger.info(
            "Using explicit VEILRENDER_FONT_CSS: %d URL(s)", len(_auto_css_urls)
        )
        return _auto_css_urls

    missing = _detect_missing_fonts()
    _needs_emoji_serving = not has_local_emoji()

    if not missing and not _needs_emoji_serving:
        logger.info("All font scripts detected locally, no CSS injection needed")
        _auto_css_urls = []
        return []

    _auto_css_urls = missing
    logger.info(
        "Auto-detected %d missing font scripts%s, will inject CSS on screenshots",
        len(missing),
        " + emoji via gateway serving" if _needs_emoji_serving else "",
    )
    return _auto_css_urls


def get_emoji_font_css(host: str, forwarded_proto: str = "") -> str | None:
    """Return inline @font-face CSS for emoji, served from gateway.

    Args:
        host: The gateway's Host header (e.g. ``localhost:7860``).
        forwarded_proto: Value of ``X-Forwarded-Proto`` header, if behind
            a reverse proxy. Falls back to port-based heuristic.

    Returns:
        Inline CSS string, or None if emoji font is available locally.
    """
    get_auto_font_css_urls()
    if not _needs_emoji_serving:
        return None
    if forwarded_proto:
        scheme = forwarded_proto
    else:
        scheme = "https" if host.endswith(":443") else "http"
    return (
        "@font-face { "
        "font-family: 'Noto Color Emoji'; "
        f"src: url({scheme}://{host}/fonts/NotoColorEmoji.ttf); "
        "}"
    )
