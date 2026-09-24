"""On-demand font download and auto-detection for screenshot i18n support."""

from __future__ import annotations

import fnmatch
import json
import logging
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from veilrender.config import settings

logger = logging.getLogger(__name__)

_RAW_GH = "https://raw.githubusercontent.com"


@dataclass(frozen=True)
class _GitHubFontSpec:
    owner: str
    repo: str
    path: str
    glob: str
    fallback_url: str


def _gf(path: str, glob: str, fallback_filename: str) -> _GitHubFontSpec:
    """Shorthand for google/fonts specs."""
    return _GitHubFontSpec(
        "google",
        "fonts",
        f"ofl/{path}",
        glob,
        f"{_RAW_GH}/google/fonts/main/ofl/{path}/{fallback_filename}",
    )


FONT_REGISTRY: dict[str, _GitHubFontSpec] = {
    "noto-sans-sc": _gf("notosanssc", "NotoSansSC*.ttf", "NotoSansSC%5Bwght%5D.ttf"),
    "noto-sans-tc": _gf("notosanstc", "NotoSansTC*.ttf", "NotoSansTC%5Bwght%5D.ttf"),
    "noto-sans-jp": _gf("notosansjp", "NotoSansJP*.ttf", "NotoSansJP%5Bwght%5D.ttf"),
    "noto-sans-kr": _gf("notosanskr", "NotoSansKR*.ttf", "NotoSansKR%5Bwght%5D.ttf"),
    "noto-color-emoji": _gf(
        "notocoloremoji", "NotoColorEmoji*.ttf", "NotoColorEmoji-Regular.ttf"
    ),
    "noto-sans-arabic": _gf(
        "notosansarabic", "NotoSansArabic*.ttf", "NotoSansArabic%5Bwdth%2Cwght%5D.ttf"
    ),
    "noto-sans-thai": _gf(
        "notosansthai", "NotoSansThai*.ttf", "NotoSansThai%5Bwdth%2Cwght%5D.ttf"
    ),
    "noto-sans-devanagari": _gf(
        "notosansdevanagari",
        "NotoSansDevanagari*.ttf",
        "NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf",
    ),
    "lxgw-wenkai": _GitHubFontSpec(
        "lxgw",
        "LxgwWenKai",
        "fonts/TTF",
        "LXGWWenKai-Regular.ttf",
        f"{_RAW_GH}/lxgw/LxgwWenKai/main/fonts/TTF/LXGWWenKai-Regular.ttf",
    ),
}

_resolved_url_cache: dict[str, tuple[str, str]] = {}


def _resolve_github_font_url(name: str, spec: _GitHubFontSpec) -> tuple[str, str]:
    """Resolve a font's download URL via GitHub Contents API.

    Returns:
        (filename, url) tuple. Uses cached result if available.
    """
    if name in _resolved_url_cache:
        return _resolved_url_cache[name]

    api_url = (
        f"https://api.github.com/repos/{spec.owner}/{spec.repo}/contents/{spec.path}"
    )
    try:
        resp = urllib.request.urlopen(api_url, timeout=10)
        entries = json.loads(resp.read())
        for entry in entries:
            if entry.get("type") == "file" and fnmatch.fnmatch(
                entry["name"], spec.glob
            ):
                filename = entry["name"]
                url = f"{_RAW_GH}/{spec.owner}/{spec.repo}/main/{spec.path}/{filename}"
                result = (filename, url)
                _resolved_url_cache[name] = result
                return result
        logger.warning(
            "No file matching %s in %s/%s/%s",
            spec.glob,
            spec.owner,
            spec.repo,
            spec.path,
        )
    except Exception:
        logger.debug(
            "GitHub API lookup failed for %s, using fallback URL", name, exc_info=True
        )

    fallback_filename = spec.fallback_url.rsplit("/", 1)[-1]
    result = (fallback_filename, spec.fallback_url)
    _resolved_url_cache[name] = result
    return result


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
                    entries.append(_resolve_github_font_url(name, FONT_REGISTRY[name]))
        elif spec in FONT_REGISTRY:
            if spec not in seen:
                seen.add(spec)
                entries.append(_resolve_github_font_url(spec, FONT_REGISTRY[spec]))
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

_auto_css_content: list[str] | None = None
_auto_detected = False
_needs_emoji_serving = False

# Font CSS cache directory
_FONT_CSS_CACHE_DIR = Path(settings.font_dir) / "css_cache"

# CDN mirrors to race for font CSS downloads
_CDN_MIRRORS: list[str] = [
    "https://cdn.jsdelivr.net/npm/@fontsource",
    "https://unpkg.com/@fontsource",
    "https://esm.sh/@fontsource",
]


def _detect_missing_fonts() -> list[str]:
    """Probe local font coverage via fc-list, return lang tags for missing scripts."""
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

    for lang in _LANG_TO_CSS:
        if lang not in installed_langs:
            missing.append(lang)

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


def _fetch_css_racing(font_name: str) -> str | None:
    """Download font CSS from the fastest CDN mirror."""
    import re as _re
    from concurrent.futures import ThreadPoolExecutor, as_completed

    css_path = font_name.split("/")[-1]

    def _try_cdn(base_url: str) -> str:
        url = f"{base_url}/{css_path}/index.css"
        if settings.font_mirror:
            url = f"{settings.font_mirror}/{url}"
        resp = urllib.request.urlopen(url, timeout=15)
        return resp.read().decode("utf-8")

    with ThreadPoolExecutor(max_workers=len(_CDN_MIRRORS)) as pool:
        futures = {pool.submit(_try_cdn, cdn): cdn for cdn in _CDN_MIRRORS}
        for future in as_completed(futures, timeout=20):
            try:
                css_text = future.result()
                # Rewrite url(./files/foo.woff2) → url(/fonts/fontsource/font-name/foo.woff2)
                css_text = _re.sub(
                    r"url\(\./files/([^)]+)\)",
                    rf"url(/fonts/fontsource/{css_path}/\1)",
                    css_text,
                )
                return css_text
            except Exception:
                continue
    return None


def _load_font_css(lang: str) -> str | None:
    """Load font CSS for a language, using local cache or CDN fetch."""
    font_name = _LANG_TO_CSS[lang]
    css_path = font_name.split("/")[-1]
    cache_file = _FONT_CSS_CACHE_DIR / f"{css_path}.css"

    if cache_file.exists():
        return cache_file.read_text("utf-8")

    logger.info("Downloading font CSS for %s from CDN (racing)...", css_path)
    css_text = _fetch_css_racing(font_name)
    if css_text:
        _FONT_CSS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(css_text, "utf-8")
        logger.info("Cached font CSS: %s (%d bytes)", css_path, len(css_text))
    else:
        logger.warning("Failed to download font CSS for %s from all CDNs", css_path)
    return css_text


def _dedup_font_faces(css_text: str) -> str:
    """Deduplicate @font-face rules by (font-family, unicode-range)."""
    import re as _re

    blocks = _re.findall(r"@font-face\s*\{[^}]+\}", css_text)
    seen: set[tuple[str, str]] = set()
    unique: list[str] = []
    for block in blocks:
        family = _re.search(r"font-family:\s*'([^']+)'", block)
        urange = _re.search(r"unicode-range:\s*([^;]+)", block)
        key = (family.group(1) if family else "", urange.group(1) if urange else "")
        if key not in seen:
            seen.add(key)
            unique.append(block)
    return "\n".join(unique)


# Combined CSS string cached after first call
_combined_css: str | None = None


def get_auto_font_css_content() -> str | None:
    """Return a single combined CSS string for missing local fonts.

    Downloads CSS from CDN on first call, rewrites font URLs to point
    to the local ``/fonts/fontsource/`` endpoint, deduplicates overlapping
    ``@font-face`` rules, and caches the result. Subsequent calls return
    cached content with no network access.
    """
    global _combined_css, _auto_detected, _needs_emoji_serving

    if _auto_detected:
        return _combined_css

    _auto_detected = True

    explicit = settings.font_css
    if explicit:
        _combined_css = None
        logger.info("Using explicit VEILRENDER_FONT_CSS (external URLs)")
        return _combined_css

    missing_langs = _detect_missing_fonts()
    _needs_emoji_serving = not has_local_emoji()

    if not missing_langs and not _needs_emoji_serving:
        logger.info("All font scripts detected locally, no CSS injection needed")
        _combined_css = None
        return None

    parts: list[str] = []
    for lang in missing_langs:
        css = _load_font_css(lang)
        if css:
            parts.append(css)

    if parts:
        _combined_css = _dedup_font_faces("\n".join(parts))
        logger.info(
            "Loaded and deduped font CSS (%d bytes from %d scripts)%s",
            len(_combined_css),
            len(parts),
            " + emoji via gateway serving" if _needs_emoji_serving else "",
        )
    else:
        _combined_css = None

    return _combined_css


def get_auto_font_css_urls() -> list[str]:
    """Return external CSS URLs for missing local fonts (legacy).

    Prefer :func:`get_auto_font_css_content` for inline injection.
    """
    get_auto_font_css_content()
    return []


def get_emoji_font_css(host: str, forwarded_proto: str = "") -> str | None:
    """Return inline @font-face CSS for emoji, served from gateway."""
    get_auto_font_css_content()
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
