"""Tests for URL validation — SSRF guards on the submitted URL.

Regression coverage for the redirect-based SSRF: the validator must reject
every non-globally-routable destination, not just the historically enumerated
private ranges (CGNAT 100.64.0.0/10 previously slipped through because the
check used ``is_private`` instead of ``is_global``).
"""

from __future__ import annotations

import pytest

from veilrender.url_validator import (
    URLValidationError,
    is_global_host,
    validate_url,
)


class TestValidateUrlRejectsNonPublic:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/",
            "http://127.1.2.3:8080/",
            "http://[::1]/",
            "http://10.0.0.1/",
            "http://172.16.5.4/",
            "http://192.168.1.1/",
            "http://169.254.169.254/latest/meta-data/",
            "http://100.64.0.1/",  # CGNAT — the regression
            "http://100.127.255.254/",  # top of the CGNAT range
        ],
    )
    def test_rejects_non_public_literal(self, url: str) -> None:
        with pytest.raises(URLValidationError):
            validate_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "file:///etc/passwd",
            "data:text/html,<h1>hi</h1>",
            "javascript:alert(1)",
            "ftp://example.com/x",
        ],
    )
    def test_rejects_non_http_scheme(self, url: str) -> None:
        with pytest.raises(URLValidationError):
            validate_url(url)

    def test_rejects_localhost_name(self) -> None:
        # Exercises the DNS path rather than an IP literal.
        with pytest.raises(URLValidationError):
            validate_url("http://localhost/")


class TestValidateUrlAcceptsPublic:
    @pytest.mark.parametrize("url", ["http://1.1.1.1/", "https://8.8.8.8/x"])
    def test_accepts_public_literal(self, url: str) -> None:
        assert validate_url(url) == url


class TestIsGlobalHost:
    @pytest.mark.parametrize(
        "host",
        [
            "127.0.0.1",
            "::1",
            "[::1]",
            "169.254.169.254",
            "10.0.0.1",
            "192.168.0.1",
            "100.64.0.1",
            "0.0.0.0",
            "",
        ],
    )
    def test_false_for_non_public(self, host: str) -> None:
        assert is_global_host(host) is False

    @pytest.mark.parametrize("host", ["1.1.1.1", "8.8.8.8", "2606:4700:4700::1111"])
    def test_true_for_public_literal(self, host: str) -> None:
        assert is_global_host(host) is True

    def test_false_for_localhost_name(self) -> None:
        assert is_global_host("localhost") is False

    def test_false_when_resolution_fails(self) -> None:
        # Unresolvable hosts are refused rather than attempted.
        assert is_global_host("nonexistent.invalid") is False
