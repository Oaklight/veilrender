"""Tests for the outbound request policy enforced on every browser request.

Regression coverage for the redirect-based SSRF: the route handler must refuse
a request whose destination is not globally routable, so that a public URL
cannot redirect the navigation into loopback or a cloud metadata endpoint.
"""

from __future__ import annotations

import asyncio

from veilrender.filters import (
    _allows_public_destination,
    make_route_handler,
    should_block,
)


class _FakeRequest:
    def __init__(self, url: str) -> None:
        self.url = url


class _FakeRoute:
    """Stands in for a patchright Route, recording what the handler did."""

    def __init__(self, url: str) -> None:
        self.request = _FakeRequest(url)
        self.aborted = False
        self.continued = False
        self.abort_reason: str | None = None

    async def abort(self, reason: str | None = None) -> None:
        self.aborted = True
        self.abort_reason = reason

    async def continue_(self) -> None:
        self.continued = True


class TestShouldBlockStillWorks:
    def test_blocks_listed_domain(self) -> None:
        assert should_block("https://ads.example.com/x", frozenset({"example.com"}))

    def test_allows_unlisted_domain(self) -> None:
        assert not should_block("https://ok.test/x", frozenset({"example.com"}))


class TestAllowsPublicDestination:
    def test_rejects_loopback(self) -> None:
        assert (
            asyncio.run(_allows_public_destination("http://127.0.0.1/", set())) is False
        )

    def test_rejects_metadata_endpoint(self) -> None:
        url = "http://169.254.169.254/latest/meta-data/"
        assert asyncio.run(_allows_public_destination(url, set())) is False

    def test_rejects_cgnat(self) -> None:
        assert (
            asyncio.run(_allows_public_destination("http://100.64.0.1/", set()))
            is False
        )

    def test_allows_public_literal(self) -> None:
        assert asyncio.run(_allows_public_destination("http://1.1.1.1/", set())) is True

    def test_allows_inline_scheme(self) -> None:
        # data:/blob: carry content inline and trigger no fetch.
        assert (
            asyncio.run(_allows_public_destination("data:text/html,x", set())) is True
        )

    def test_rejects_missing_hostname(self) -> None:
        assert asyncio.run(_allows_public_destination("http:///path", set())) is False

    def test_records_refusal_in_cache(self) -> None:
        blocked: set[str] = set()
        asyncio.run(_allows_public_destination("http://127.0.0.1/", blocked))
        assert "127.0.0.1" in blocked


class TestRouteHandlerEnforcesDestination:
    def test_aborts_redirect_to_loopback(self) -> None:
        handler = make_route_handler(frozenset())
        route = _FakeRoute("http://127.0.0.1:7860/health")
        asyncio.run(handler(route))
        assert route.aborted
        assert not route.continued

    def test_continues_public_request(self) -> None:
        handler = make_route_handler(frozenset())
        route = _FakeRoute("http://1.1.1.1/")
        asyncio.run(handler(route))
        assert route.continued
        assert not route.aborted

    def test_blocklist_takes_precedence(self) -> None:
        handler = make_route_handler(frozenset({"ads.example.com"}))
        route = _FakeRoute("https://ads.example.com/a.js")
        asyncio.run(handler(route))
        assert route.aborted

    def test_repeat_private_host_uses_cache(self) -> None:
        handler = make_route_handler(frozenset())
        first = _FakeRoute("http://127.0.0.1/a")
        second = _FakeRoute("http://127.0.0.1/b")
        asyncio.run(handler(first))
        asyncio.run(handler(second))
        assert first.aborted and second.aborted
