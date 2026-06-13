"""Application settings loaded from environment variables."""

from __future__ import annotations

import os


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


settings = Settings()
