"""Outbound request filtering using community-maintained blocklists.

Blocks ad networks, trackers, and beacons at the Playwright level to reduce
unnecessary outbound connections and prevent abuse of the rendering service.

Blocklist source: StevenBlack/hosts (MIT license)
https://github.com/StevenBlack/hosts
"""

from __future__ import annotations

import importlib.resources
import logging
from urllib.parse import urlparse

from patchright.async_api import Route

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
    """Create a Playwright route handler that blocks requests to listed domains.

    Args:
        blocklist: Set of blocked domain names.

    Returns:
        An async route handler function for use with ``page.route()``.
    """

    async def _handle_route(route: Route) -> None:
        url = route.request.url
        if should_block(url, blocklist):
            logger.info("Blocked: %s", url[:200])
            await route.abort("blockedbyclient")
        else:
            await route.continue_()

    return _handle_route
