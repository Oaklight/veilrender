"""Tests for ScreenshotRequest model — from_dict and validate."""

from __future__ import annotations

import pytest

from veilrender.models import ClipRegion, ScreenshotRequest


# ---------------------------------------------------------------------------
# from_dict — defaults
# ---------------------------------------------------------------------------


class TestFromDictDefaults:
    def test_minimal(self):
        req = ScreenshotRequest.from_dict({"url": "https://example.com"})
        assert req.url == "https://example.com"
        assert req.full_page is False
        assert req.wait_until == "networkidle"
        assert req.timeout is None
        assert req.viewport_width is None
        assert req.viewport_height is None
        assert req.font_css is None
        assert req.format == "png"
        assert req.quality is None
        assert req.scale is None
        assert req.selector is None
        assert req.clip is None
        assert req.color_scheme is None
        assert req.wait_for is None
        assert req.transparent is False


# ---------------------------------------------------------------------------
# from_dict — new fields
# ---------------------------------------------------------------------------


class TestFromDictNewFields:
    def test_format_jpeg(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "format": "jpeg", "quality": 80}
        )
        assert req.format == "jpeg"
        assert req.quality == 80

    def test_scale(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com", "scale": 2.0})
        assert req.scale == 2.0

    def test_selector(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com", "selector": "#main"})
        assert req.selector == "#main"

    def test_clip(self):
        req = ScreenshotRequest.from_dict(
            {
                "url": "https://x.com",
                "clip": {"x": 10, "y": 20, "width": 300, "height": 400},
            }
        )
        assert isinstance(req.clip, ClipRegion)
        assert req.clip.x == 10.0
        assert req.clip.y == 20.0
        assert req.clip.width == 300.0
        assert req.clip.height == 400.0

    def test_color_scheme(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "color_scheme": "dark"}
        )
        assert req.color_scheme == "dark"

    def test_wait_for(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "wait_for": ".loaded"}
        )
        assert req.wait_for == ".loaded"

    def test_transparent(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com", "transparent": True})
        assert req.transparent is True


# ---------------------------------------------------------------------------
# from_dict — clip parsing errors
# ---------------------------------------------------------------------------


class TestFromDictClipErrors:
    def test_clip_not_dict(self):
        with pytest.raises(ValueError, match="clip must be an object"):
            ScreenshotRequest.from_dict({"url": "https://x.com", "clip": "bad"})

    def test_clip_missing_keys(self):
        with pytest.raises(ValueError, match="missing: width, height"):
            ScreenshotRequest.from_dict(
                {"url": "https://x.com", "clip": {"x": 0, "y": 0}}
            )

    def test_clip_non_numeric(self):
        with pytest.raises(ValueError, match="clip values must be numeric"):
            ScreenshotRequest.from_dict(
                {
                    "url": "https://x.com",
                    "clip": {"x": "a", "y": 0, "width": 10, "height": 10},
                }
            )


# ---------------------------------------------------------------------------
# validate — passing cases
# ---------------------------------------------------------------------------


class TestValidatePass:
    def test_defaults_valid(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com"})
        req.validate()

    def test_jpeg_with_quality(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "format": "jpeg", "quality": 50}
        )
        req.validate()

    def test_quality_bounds(self):
        for q in (0, 100):
            req = ScreenshotRequest.from_dict(
                {"url": "https://x.com", "format": "jpeg", "quality": q}
            )
            req.validate()

    def test_clip_with_full_page(self):
        req = ScreenshotRequest.from_dict(
            {
                "url": "https://x.com",
                "full_page": True,
                "clip": {"x": 0, "y": 0, "width": 100, "height": 100},
            }
        )
        req.validate()

    def test_scale_positive(self):
        for s in (0.5, 1, 2, 3.0):
            req = ScreenshotRequest.from_dict({"url": "https://x.com", "scale": s})
            req.validate()

    def test_transparent_png(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com", "transparent": True})
        req.validate()


# ---------------------------------------------------------------------------
# validate — failing cases
# ---------------------------------------------------------------------------


class TestValidateFail:
    def test_unsupported_format(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com", "format": "bmp"})
        with pytest.raises(ValueError, match="Unsupported format 'bmp'"):
            req.validate()

    def test_webp_not_yet_supported(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com", "format": "webp"})
        with pytest.raises(ValueError, match="webp is not yet supported"):
            req.validate()

    def test_quality_without_jpeg(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "format": "png", "quality": 80}
        )
        with pytest.raises(ValueError, match="quality is only supported for jpeg"):
            req.validate()

    def test_quality_out_of_range(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "format": "jpeg", "quality": 101}
        )
        with pytest.raises(ValueError, match="quality must be between 0 and 100"):
            req.validate()

    def test_quality_negative(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "format": "jpeg", "quality": -1}
        )
        with pytest.raises(ValueError, match="quality must be between 0 and 100"):
            req.validate()

    def test_scale_zero(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com", "scale": 0})
        with pytest.raises(ValueError, match="scale must be a positive number"):
            req.validate()

    def test_scale_negative(self):
        req = ScreenshotRequest.from_dict({"url": "https://x.com", "scale": -1})
        with pytest.raises(ValueError, match="scale must be a positive number"):
            req.validate()

    def test_selector_and_clip(self):
        req = ScreenshotRequest.from_dict(
            {
                "url": "https://x.com",
                "selector": "#main",
                "clip": {"x": 0, "y": 0, "width": 100, "height": 100},
            }
        )
        with pytest.raises(
            ValueError, match="selector and clip are mutually exclusive"
        ):
            req.validate()

    def test_selector_and_full_page(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "selector": "#main", "full_page": True}
        )
        with pytest.raises(
            ValueError, match="selector and full_page are mutually exclusive"
        ):
            req.validate()

    def test_transparent_jpeg(self):
        req = ScreenshotRequest.from_dict(
            {"url": "https://x.com", "format": "jpeg", "transparent": True}
        )
        with pytest.raises(ValueError, match="transparent is not supported with jpeg"):
            req.validate()

    def test_clip_non_positive_width(self):
        req = ScreenshotRequest.from_dict(
            {
                "url": "https://x.com",
                "clip": {"x": 0, "y": 0, "width": 0, "height": 100},
            }
        )
        with pytest.raises(ValueError, match="clip width and height must be positive"):
            req.validate()

    def test_clip_negative_height(self):
        req = ScreenshotRequest.from_dict(
            {
                "url": "https://x.com",
                "clip": {"x": 0, "y": 0, "width": 100, "height": -5},
            }
        )
        with pytest.raises(ValueError, match="clip width and height must be positive"):
            req.validate()
