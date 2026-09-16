"""Per-IP request rate limiting for render and screenshot endpoints.

Parses the ``VEILRENDER_RATE_LIMIT`` config (e.g. ``"10/60"`` = 10
requests per 60-second sliding window) and exposes a
:func:`check_rate_limit` helper that route handlers call after auth.
Returns a 429 response with ``Retry-After`` header when a client IP
exceeds the limit, or ``None`` if the request is allowed.
"""

from __future__ import annotations

import logging
import math

from veilrender._vendor.httpserver import Request, Response
from veilrender._vendor.ratelimit import SlidingWindowLimiter
from veilrender.config import settings

logger = logging.getLogger(__name__)

# Module-level limiter — created once at import time, shared across requests.
_limiter: SlidingWindowLimiter | None = None


def _parse_rate_limit(value: str) -> tuple[int, int] | None:
    """Parse ``"N/S"`` into (max_requests, window_seconds).

    Returns ``None`` if the string is empty or malformed.
    """
    value = value.strip()
    if not value:
        return None
    parts = value.split("/")
    if len(parts) != 2:
        logger.warning("Invalid VEILRENDER_RATE_LIMIT format: %r (expected N/S)", value)
        return None
    try:
        max_requests = int(parts[0])
        window_seconds = int(parts[1])
    except ValueError:
        logger.warning(
            "Invalid VEILRENDER_RATE_LIMIT values: %r (N and S must be integers)",
            value,
        )
        return None
    if max_requests <= 0 or window_seconds <= 0:
        logger.warning("VEILRENDER_RATE_LIMIT values must be positive: %r", value)
        return None
    return max_requests, window_seconds


def _init_limiter() -> SlidingWindowLimiter | None:
    """Create a limiter from config, or return None if disabled."""
    parsed = _parse_rate_limit(settings.rate_limit)
    if parsed is None:
        return None
    max_requests, window_seconds = parsed
    logger.info(
        "Rate limiting enabled: %d requests per %ds window",
        max_requests,
        window_seconds,
    )
    return SlidingWindowLimiter(limit=max_requests, window_seconds=window_seconds)


_limiter = _init_limiter()


def _get_client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For header or peer address."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client_addr[0] if hasattr(request, "client_addr") else "unknown"


def check_rate_limit(request: Request) -> Response | None:
    """Check per-IP rate limit for the given request.

    Returns a 429 ``Response`` with ``Retry-After`` header if the
    client IP has exceeded the configured rate limit, or ``None`` if
    the request is allowed (or rate limiting is disabled).
    """
    if _limiter is None:
        return None

    ip = _get_client_ip(request)
    result = _limiter.acquire(ip)

    if result.allowed:
        return None

    retry_after = math.ceil(result.retry_after) if result.retry_after else 1
    logger.warning("Rate limit exceeded for IP %s (retry_after=%ds)", ip, retry_after)
    return Response(
        body=b'{"error": "Too many requests"}',
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content_type="application/json",
    )
