"""Request and response data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

WaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]
ScreenshotFormat = Literal["png", "jpeg"]
ColorScheme = Literal["light", "dark", "no-preference"]

_SUPPORTED_FORMATS: set[str] = {"png", "jpeg"}


@dataclass
class ClipRegion:
    """Rectangular clip region for screenshots."""

    x: float
    y: float
    width: float
    height: float


@dataclass
class RenderRequest:
    """POST /render request body."""

    url: str
    formats: list[str] = field(
        default_factory=lambda: ["html", "markdown", "readability"]
    )
    wait_until: WaitUntil = "networkidle"
    timeout: int | None = None  # ms, None = use default

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RenderRequest:
        """Create from parsed JSON dict."""
        return cls(
            url=data["url"],
            formats=data.get("formats", ["html", "markdown", "readability"]),
            wait_until=data.get("wait_until", "networkidle"),
            timeout=data.get("timeout"),
        )


@dataclass
class ScreenshotRequest:
    """POST /screenshot request body."""

    url: str
    full_page: bool = False
    wait_until: WaitUntil = "networkidle"
    timeout: int | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    font_css: str | None = None
    format: ScreenshotFormat = "png"
    quality: int | None = None
    scale: float | None = None
    selector: str | None = None
    clip: ClipRegion | None = None
    color_scheme: ColorScheme | None = None
    wait_for: str | None = None
    transparent: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScreenshotRequest:
        """Create from parsed JSON dict."""
        clip_data = data.get("clip")
        clip: ClipRegion | None = None
        if clip_data is not None:
            if not isinstance(clip_data, dict):
                raise ValueError("clip must be an object with x, y, width, height")
            missing = [k for k in ("x", "y", "width", "height") if k not in clip_data]
            if missing:
                raise ValueError(
                    f"clip must have x, y, width, and height (missing: {', '.join(missing)})"
                )
            try:
                clip = ClipRegion(
                    x=float(clip_data["x"]),
                    y=float(clip_data["y"]),
                    width=float(clip_data["width"]),
                    height=float(clip_data["height"]),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"clip values must be numeric: {exc}") from exc

        return cls(
            url=data["url"],
            full_page=data.get("full_page", False),
            wait_until=data.get("wait_until", "networkidle"),
            timeout=data.get("timeout"),
            viewport_width=data.get("viewport_width"),
            viewport_height=data.get("viewport_height"),
            font_css=data.get("font_css"),
            format=data.get("format", "png"),
            quality=data.get("quality"),
            scale=data.get("scale"),
            selector=data.get("selector"),
            clip=clip,
            color_scheme=data.get("color_scheme"),
            wait_for=data.get("wait_for"),
            transparent=data.get("transparent", False),
        )

    def validate(self) -> None:
        """Validate parameter combinations. Raises ValueError on invalid input."""
        if self.format not in _SUPPORTED_FORMATS:
            msg = f"Unsupported format '{self.format}'"
            if self.format == "webp":
                msg += " (webp is not yet supported)"
            else:
                msg += f". Supported: {', '.join(sorted(_SUPPORTED_FORMATS))}"
            raise ValueError(msg)

        if self.quality is not None:
            if self.format != "jpeg":
                raise ValueError("quality is only supported for jpeg format")
            if not (0 <= self.quality <= 100):
                raise ValueError("quality must be between 0 and 100")

        if self.scale is not None and self.scale <= 0:
            raise ValueError("scale must be a positive number")

        if self.selector and self.clip:
            raise ValueError("selector and clip are mutually exclusive")

        if self.selector and self.full_page:
            raise ValueError("selector and full_page are mutually exclusive")

        if self.transparent and self.format == "jpeg":
            raise ValueError("transparent is not supported with jpeg format")

        if self.clip:
            if self.clip.width <= 0 or self.clip.height <= 0:
                raise ValueError("clip width and height must be positive")


@dataclass
class LinkInfo:
    """Extracted link from a page."""

    url: str
    text: str


@dataclass
class PageMetadata:
    """Metadata extracted from a rendered page."""

    title: str
    url: str
    status_code: int


@dataclass
class RenderContent:
    """Rendered content in multiple formats."""

    html: str | None = None
    markdown: str | None = None
    readability: str | None = None


@dataclass
class RenderResponse:
    """POST /render response body."""

    content: RenderContent
    metadata: PageMetadata
    links: list[LinkInfo]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "content": {
                k: v
                for k, v in {
                    "html": self.content.html,
                    "markdown": self.content.markdown,
                    "readability": self.content.readability,
                }.items()
                if v is not None
            },
            "metadata": {
                "title": self.metadata.title,
                "url": self.metadata.url,
                "status_code": self.metadata.status_code,
            },
            "links": [{"url": link.url, "text": link.text} for link in self.links],
        }
