"""Outbound request filtering using community-maintained blocklists.

Blocks ad networks, trackers, and beacons at the Playwright level to reduce
unnecessary outbound connections and prevent abuse of the rendering service.

Blocklist source: StevenBlack/hosts (MIT license)
https://github.com/StevenBlack/hosts
"""

from __future__ import annotations

import asyncio
import importlib.resources
import logging
from urllib.parse import urlparse

from patchright.async_api import Route

from veilrender.url_validator import is_global_host

logger = logging.getLogger(__name__)


def load_blocklist(extra_domains: list[str] | None = None) -> frozenset[str]:
    """Load the blocklist from the bundled data file.

    Args:
        extra_domains: Additional domains to block beyond the bundled list.

    Returns:
        A frozen set of blocked domain names for O(1) lookup.
    """
    domains: set[str] = set()

    try:
        ref = importlib.resources.files("veilrender.data").joinpath("blocklist.txt")
        text = ref.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                domains.add(line.lower())
    except Exception:
        logger.warning("Failed to load bundled blocklist, filtering disabled")

    if extra_domains:
        for d in extra_domains:
            d = d.strip().lower()
            if d:
                domains.add(d)

    logger.info("Loaded blocklist with %d domains", len(domains))
    return frozenset(domains)


def should_block(url: str, blocklist: frozenset[str]) -> bool:
    """Check if a URL should be blocked based on the blocklist.

    Performs suffix matching: for hostname ``a.b.c.com``, checks
    ``a.b.c.com``, ``b.c.com``, ``c.com`` against the set.

    Args:
        url: The request URL to check.
        blocklist: Set of blocked domain names.

    Returns:
        True if the URL's domain matches the blocklist.
    """
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        hostname = hostname.lower()

        # Walk up the domain hierarchy
        parts = hostname.split(".")
        for i in range(len(parts)):
            candidate = ".".join(parts[i:])
            if candidate in blocklist:
                return True
    except Exception:
        pass

    return False


def make_route_handler(blocklist: frozenset[str]):
    """Create a Playwright route handler enforcing the outbound request policy.

    Two checks run on every request the browser issues, including requests
    produced by a redirect or by a subresource fetch:

    1. The blocklist (ad/tracker domains) is matched by domain suffix.
    2. The destination host must resolve only to globally routable addresses,
       so a redirect cannot bounce the navigation into loopback, RFC1918, the
       cloud metadata endpoint, or any other non-public range.

    Checking the destination rather than the URL the caller submitted is what
    closes the redirect-based SSRF: the submitted URL passes validation, but
    the hop it redirects to does not.

    Args:
        blocklist: Set of blocked domain names.

    Returns:
        An async route handler function for use with ``page.route()``.
    """

    # Hostnames already found to be non-public stay blocked for the life of the
    # handler. Only refusals are cached: caching an allow would let a host that
    # later resolves to a private address slip through.
    blocked_hosts: set[str] = set()

    async def _handle_route(route: Route) -> None:
        url = route.request.url

        if should_block(url, blocklist):
            logger.info("Blocked (blocklist): %s", url[:200])
            await route.abort("blockedbyclient")
            return

        if not await _allows_public_destination(url, blocked_hosts):
            logger.warning("Blocked (non-public destination): %s", url[:200])
            await route.abort("blockedbyclient")
            return

        await route.continue_()

    return _handle_route


async def _allows_public_destination(url: str, blocked_hosts: set[str]) -> bool:
    """Check that a request URL points at a globally routable host.

    Non-network schemes (``data:``, ``blob:``, ``about:``) carry inline
    content rather than triggering a fetch, so they are allowed through. DNS
    resolution blocks, so it runs in a worker thread to avoid stalling the
    event loop.

    Args:
        url: The request URL the browser is about to issue.
        blocked_hosts: Cache of hostnames already known to be non-public.
            Refusals are recorded here.

    Returns:
        True if the request may proceed.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return True

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False
    if hostname in blocked_hosts:
        return False

    allowed = await asyncio.to_thread(is_global_host, hostname)
    if not allowed:
        blocked_hosts.add(hostname)
    return allowed
