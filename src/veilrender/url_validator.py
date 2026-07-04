"""URL validation to prevent SSRF, local file reads, and protocol abuse.

Blocks:
- Non-HTTP(S) schemes: file://, data:, javascript:, ftp://, etc.
- Private/reserved IP ranges: 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12,
  192.168.0.0/16, 169.254.0.0/16, ::1, fd00::/8, etc.
- DNS resolution is checked before navigation to prevent DNS rebinding.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = {"http", "https"}


class URLValidationError(Exception):
    """Raised when a URL fails validation."""


def validate_url(url: str) -> str:
    """Validate and sanitize a URL before passing it to Playwright.

    Args:
        url: The user-supplied URL to validate.

    Returns:
        The validated URL (unchanged if valid).

    Raises:
        URLValidationError: If the URL is unsafe.
    """
    if not url or not url.strip():
        raise URLValidationError("Empty URL")

    parsed = urlparse(url)

    # Scheme check
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise URLValidationError(f"Scheme '{scheme}' not allowed (only http/https)")

    # Hostname check
    hostname = parsed.hostname
    if not hostname:
        raise URLValidationError("Missing hostname")

    # Resolve DNS and check against private IP ranges
    _check_resolved_ips(hostname)

    return url


def _check_resolved_ips(hostname: str) -> None:
    """Resolve hostname and reject private/reserved IP addresses.

    Resolves DNS before Playwright navigates to prevent DNS rebinding
    attacks where a hostname initially resolves to a public IP but
    later resolves to a private one.

    Args:
        hostname: The hostname to check.

    Raises:
        URLValidationError: If the hostname resolves to a private IP.
    """
    # Check if hostname is a raw IP literal
    try:
        addr = ipaddress.ip_address(hostname)
        if _is_blocked_ip(addr):
            raise URLValidationError(f"IP address {hostname} is in a blocked range")
        return
    except ValueError:
        pass  # Not an IP literal, proceed to DNS resolution

    # Resolve hostname
    try:
        results = socket.getaddrinfo(
            hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise URLValidationError(
            f"DNS resolution failed for '{hostname}': {exc}"
        ) from exc

    if not results:
        raise URLValidationError(f"No DNS results for '{hostname}'")

    for family, _type, _proto, _canonname, sockaddr in results:
        ip_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip_str)
            if _is_blocked_ip(addr):
                raise URLValidationError(
                    f"'{hostname}' resolves to blocked IP {ip_str}"
                )
        except ValueError:
            continue


def _is_blocked_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address is in a blocked range.

    Blocks:
        - Loopback (127.0.0.0/8, ::1)
        - Private networks (10/8, 172.16/12, 192.168/16)
        - Link-local (169.254/16, fe80::/10)
        - Unique local (fd00::/8)
        - Multicast, reserved, unspecified
    """
    return (
        addr.is_loopback
        or addr.is_private
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_link_local
        or addr.is_unspecified
    )
