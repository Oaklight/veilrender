"""Application settings loaded from environment variables."""

from __future__ import annotations

import os


def _parse_worker_entry(entry: str) -> tuple[str, str]:
    """Parse a worker entry into (protocol, endpoint).

    Supported formats:
    - ``cdp://host:9222`` → ("cdp", "http://host:9222")
    - ``playwright://host:1234/path`` → ("playwright", "ws://host:1234/path")
    - ``playwrights://host:1234/path`` → ("playwright", "wss://host:1234/path")
    - ``obscura://host:9223`` → ("obscura", "http://host:9223")
    - ``http://host:9222`` → ("cdp", "http://host:9222")
    - ``host:9222`` → ("cdp", "http://host:9222")
    """
    if entry.startswith("obscura://"):
        return ("obscura", "http://" + entry[len("obscura://") :])
    if entry.startswith("playwrights://"):
        return ("playwright", "wss://" + entry[len("playwrights://") :])
    if entry.startswith("playwright://"):
        return ("playwright", "ws://" + entry[len("playwright://") :])
    if entry.startswith("cdp://"):
        return ("cdp", "http://" + entry[len("cdp://") :])
    if entry.startswith(("http://", "https://", "ws://", "wss://")):
        return ("cdp", entry)
    return ("cdp", "http://" + entry)


class Settings:
    """Configuration from ``VEILRENDER_*`` environment variables."""

    def __init__(self) -> None:
        self.api_token: str | None = os.environ.get("VEILRENDER_API_TOKEN")
        self.port: int = int(os.environ.get("VEILRENDER_PORT", "7860"))
        self.host: str = os.environ.get("VEILRENDER_HOST", "0.0.0.0")
        self.timeout: int = int(os.environ.get("VEILRENDER_TIMEOUT", "30000"))
        self.viewport_width: int = int(
            os.environ.get("VEILRENDER_VIEWPORT_WIDTH", "1280")
        )
        self.viewport_height: int = int(
            os.environ.get("VEILRENDER_VIEWPORT_HEIGHT", "720")
        )
        self.max_concurrent: int = int(os.environ.get("VEILRENDER_MAX_CONCURRENT", "5"))

        # Queue depth limit — 0 means unlimited
        self.max_queue: int = int(os.environ.get("VEILRENDER_MAX_QUEUE", "0"))

        # Remote browser worker pool
        # Format: cdp://host:9222,playwright://host:1234/ws-path
        # No prefix or http:// defaults to cdp://
        _workers_raw = os.environ.get("VEILRENDER_WORKERS", "")
        self.workers: list[tuple[str, str]] = (
            [
                _parse_worker_entry(w.strip())
                for w in _workers_raw.split(",")
                if w.strip()
            ]
            if _workers_raw
            else []
        )
        self.worker_max_concurrent: int = int(
            os.environ.get("VEILRENDER_WORKER_MAX_CONCURRENT", str(self.max_concurrent))
        )
        self.worker_health_interval: int = int(
            os.environ.get("VEILRENDER_WORKER_HEALTH_INTERVAL", "10")
        )

        # Obscura lightweight browser (tier-0 with fallback to CloakBrowser)
        self.obscura_enabled: bool = (
            os.environ.get("VEILRENDER_OBSCURA", "false").lower() == "true"
        )
        self.obscura_max_concurrent: int = int(
            os.environ.get(
                "VEILRENDER_OBSCURA_MAX_CONCURRENT", str(self.max_concurrent)
            )
        )
        # Tier-0 deadline (ms) before speculative tier-1 starts racing
        self.obscura_timeout: int = int(
            os.environ.get("VEILRENDER_OBSCURA_TIMEOUT", "10000")
        )

        # Hard request deadline (seconds) — kills entire pipeline, returns 504
        self.request_deadline: int = int(
            os.environ.get("VEILRENDER_REQUEST_DEADLINE", "45")
        )

        # Opaque engine tag in X-Render-Engine response header
        self.render_engine_header: bool = (
            os.environ.get("VEILRENDER_ENGINE_HEADER", "false").lower() == "true"
        )

        # Font download
        _fonts_raw = os.environ.get("VEILRENDER_FONTS", "")
        self.fonts: list[str] = (
            [f.strip() for f in _fonts_raw.split(",") if f.strip()]
            if _fonts_raw
            else []
        )
        self.font_dir: str = os.environ.get(
            "VEILRENDER_FONT_DIR", os.path.expanduser("~/.fonts")
        )
        self.font_mirror: str = os.environ.get("VEILRENDER_FONT_MIRROR", "")
        self.font_css: str = os.environ.get("VEILRENDER_FONT_CSS", "")

        self.resource_filter: bool = (
            os.environ.get("VEILRENDER_RESOURCE_FILTER", "true").lower() == "true"
        )
        _extra = os.environ.get("VEILRENDER_BLOCKED_DOMAINS_EXTRA", "")
        self.blocked_domains_extra: list[str] = (
            [d.strip() for d in _extra.split(",") if d.strip()] if _extra else []
        )

        # Cache settings
        self.cache_enabled: bool = (
            os.environ.get("VEILRENDER_CACHE_ENABLED", "false").lower() == "true"
        )
        self.cache_ttl: int = int(os.environ.get("VEILRENDER_CACHE_TTL", "86400"))
        self.cache_l1_maxsize: int = int(
            os.environ.get("VEILRENDER_CACHE_L1_MAXSIZE", "100")
        )

        # Per-IP request rate limiting
        # Format: "N/S" where N = max requests, S = window in seconds
        # Example: "10/60" = 10 requests per 60 seconds
        # Empty string (default) = rate limiting disabled
        self.rate_limit: str = os.environ.get("VEILRENDER_RATE_LIMIT", "")

        # S3-compatible storage (Cloudflare R2, Oracle Object Storage, etc.)
        self.s3_endpoint: str | None = os.environ.get("VEILRENDER_S3_ENDPOINT")
        self.s3_access_key: str | None = os.environ.get("VEILRENDER_S3_ACCESS_KEY")
        self.s3_secret_key: str | None = os.environ.get("VEILRENDER_S3_SECRET_KEY")
        self.s3_bucket: str = os.environ.get("VEILRENDER_S3_BUCKET", "veilrender-cache")
        self.s3_region: str = os.environ.get("VEILRENDER_S3_REGION", "auto")
        self.s3_secure: bool = (
            os.environ.get("VEILRENDER_S3_SECURE", "true").lower() == "true"
        )


settings = Settings()
