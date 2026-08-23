"""Application settings loaded from environment variables."""

from __future__ import annotations

import os


def _parse_worker_entry(entry: str) -> tuple[str, str]:
    """Parse a worker entry into (protocol, endpoint).

    Supported formats:
    - ``cdp://host:9222`` → ("cdp", "http://host:9222")
    - ``playwright://host:1234/path`` → ("playwright", "ws://host:1234/path")
    - ``http://host:9222`` → ("cdp", "http://host:9222")
    - ``host:9222`` → ("cdp", "http://host:9222")
    """
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
