"""Token-based authentication with IP-based rate limiting.

Failed auth attempts are tracked per IP. After 3 failures within a
rolling window, the IP is banned for a configurable duration.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from veilrender._vendor.httpserver import HTTPException, Request
from veilrender.config import settings

logger = logging.getLogger(__name__)

# Fail2ban settings
_MAX_FAILURES = 3
_WINDOW_SECONDS = 300  # 5 minute rolling window
_BAN_SECONDS = 600  # 10 minute ban

# State: per-IP failure timestamps and ban expiry
_failures: dict[str, list[float]] = defaultdict(list)
_banned: dict[str, float] = {}


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # Take the first (leftmost) IP — the original client
        return forwarded.split(",")[0].strip()
    return request.client_addr[0] if hasattr(request, "client_addr") else "unknown"


def _is_banned(ip: str) -> bool:
    """Check if an IP is currently banned."""
    ban_until = _banned.get(ip)
    if ban_until is None:
        return False
    if time.monotonic() >= ban_until:
        del _banned[ip]
        return False
    return True


def _record_failure(ip: str) -> None:
    """Record an auth failure and ban if threshold exceeded."""
    now = time.monotonic()

    # Clean old entries outside the window
    _failures[ip] = [t for t in _failures[ip] if now - t < _WINDOW_SECONDS]
    _failures[ip].append(now)

    if len(_failures[ip]) >= _MAX_FAILURES:
        _banned[ip] = now + _BAN_SECONDS
        _failures.pop(ip, None)
        logger.warning(
            "IP %s banned for %ds after %d auth failures",
            ip,
            _BAN_SECONDS,
            _MAX_FAILURES,
        )


def _clear_failures(ip: str) -> None:
    """Clear failure history on successful auth."""
    _failures.pop(ip, None)


def verify_token(request: Request) -> None:
    """Verify the API token from header or query param.

    Checks ``Authorization: Bearer <token>`` header first, then falls
    back to ``?token=<token>`` query parameter.

    Raises:
        HTTPException: 403 if IP is banned, 401 if token is invalid,
            403 if token is missing.

    If ``VEILRENDER_API_TOKEN`` is not configured, auth is disabled.
    """
    expected = settings.api_token
    if expected is None:
        return

    ip = _get_client_ip(request)

    # Check ban first
    if _is_banned(ip):
        raise HTTPException(403, "Temporarily banned due to repeated auth failures")

    # Check Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token == expected:
            _clear_failures(ip)
            return
        _record_failure(ip)
        raise HTTPException(401, "Invalid token")

    # Check query param
    token_params = request.query_params.get("token", [])
    if token_params:
        if token_params[0] == expected:
            _clear_failures(ip)
            return
        _record_failure(ip)
        raise HTTPException(401, "Invalid token")

    _record_failure(ip)
    raise HTTPException(403, "Authentication required")
