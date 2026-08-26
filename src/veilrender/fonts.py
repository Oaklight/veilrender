"""On-demand font download for screenshot i18n support."""

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


def ensure_fonts(font_specs: list[str]) -> None:
    """Download fonts that are not already present."""
    font_dir = Path(settings.font_dir)
    font_dir.mkdir(parents=True, exist_ok=True)

    entries = _resolve_entries(font_specs)
    if not entries:
        return

    downloaded = 0
    for filename, url in entries:
        dest = font_dir / filename
        if dest.exists():
            logger.debug("Font already present: %s", dest)
            continue

        if settings.font_mirror:
            url = f"{settings.font_mirror}/{url}"

        logger.info("Downloading font: %s", filename)
        try:
            urllib.request.urlretrieve(url, str(dest))
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
