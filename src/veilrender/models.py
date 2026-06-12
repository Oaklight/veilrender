"""Request and response data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

WaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScreenshotRequest:
        """Create from parsed JSON dict."""
        return cls(
            url=data["url"],
            full_page=data.get("full_page", False),
            wait_until=data.get("wait_until", "networkidle"),
            timeout=data.get("timeout"),
            viewport_width=data.get("viewport_width"),
            viewport_height=data.get("viewport_height"),
        )


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
