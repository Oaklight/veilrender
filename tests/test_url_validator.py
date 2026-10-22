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
            "http://[::ffff:127.0.0.1]/",  # IPv4-mapped loopback
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
            "::ffff:127.0.0.1",
            "::ffff:10.0.0.1",
            "224.0.0.1",
            "239.255.255.250",
            "ff02::1",
            "192.0.2.1",  # TEST-NET-1
            "64:ff9b::7f00:1",  # NAT64 encoding of 127.0.0.1
            "64:ff9b::a9fe:a9fe",  # NAT64 encoding of 169.254.169.254
            "64:ff9b:1::1",  # local-use NAT64
            "2002:7f00:1::",  # 6to4 encoding of 127.0.0.1
            "2001::1",  # Teredo
            "5f00::1",  # SRv6 SIDs
            "",
        ],
    )
    def test_false_for_non_public(self, host: str) -> None:
        assert is_global_host(host) is False

    @pytest.mark.parametrize(
        "host",
        [
            "1.1.1.1",
            "8.8.8.8",
            "2606:4700:4700::1111",
            "::ffff:8.8.8.8",
            "64:ff9b::808:808",  # NAT64 encoding of 8.8.8.8
        ],
    )
    def test_true_for_public_literal(self, host: str) -> None:
        assert is_global_host(host) is True

    def test_false_for_localhost_name(self) -> None:
        assert is_global_host("localhost") is False

    def test_false_when_resolution_fails(self) -> None:
        # Unresolvable hosts are refused rather than attempted.
        assert is_global_host("nonexistent.invalid") is False
