"""URL validation to prevent SSRF, local file reads, and protocol abuse.

Blocks:
- Non-HTTP(S) schemes: file://, data:, javascript:, ftp://, etc.
- Every address outside the globally routable space, via an ``is_global``
  allowlist: loopback, RFC1918, link-local (incl. the 169.254.169.254 cloud
  metadata address), CGNAT 100.64.0.0/10, unique-local, multicast, reserved.
- DNS resolution is checked before navigation to prevent DNS rebinding.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_ALLOWED_SCHEMES = {"http", "https"}

_BINARY_EXTENSIONS = frozenset(
    {
        ".parquet",
        ".zip",
        ".tar.gz",
        ".tgz",
        ".7z",
        ".rar",
        ".bz2",
        ".xz",
        ".gz",
        ".exe",
        ".msi",
        ".dmg",
        ".deb",
        ".rpm",
        ".bin",
        ".iso",
        ".whl",
        ".egg",
        ".apk",
        ".ipa",
    }
)


class URLValidationError(Exception):
    """Raised when a URL fails validation."""


def _has_binary_extension(path: str) -> str | None:
    """Return the matched binary extension, or None."""
    lower = path.lower()
    for ext in sorted(_BINARY_EXTENSIONS, key=len, reverse=True):
        if lower.endswith(ext):
            return ext
    return None


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

    # Reject URLs pointing to binary/downloadable files (before DNS to skip the round-trip)
    ext = _has_binary_extension(parsed.path)
    if ext:
        raise URLValidationError(
            f"URL points to a binary file ({ext}), not a renderable page"
        )

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
        if is_blocked_ip(addr):
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
            if is_blocked_ip(addr):
                raise URLValidationError(
                    f"'{hostname}' resolves to blocked IP {ip_str}"
                )
        except ValueError:
            continue


_SPECIAL_PURPOSE_NETWORKS = tuple(
    ipaddress.ip_network(net)
    for net in (
        "192.0.0.0/24",  # IETF protocol assignments
        "192.88.99.0/24",  # 6to4 relay anycast (deprecated)
        "198.18.0.0/15",  # benchmarking
        "240.0.0.0/4",  # reserved, incl. broadcast
        "64:ff9b:1::/48",  # local-use NAT64
        "::/96",  # IPv4-compatible (deprecated)
        "100::/64",  # discard-only
        "2001::/32",  # Teredo (embeds IPv4)
        "2001:2::/48",  # benchmarking
        "2001:10::/28",  # ORCHID
        "2001:20::/28",  # ORCHIDv2
        "2001:db8::/32",  # documentation
        "2002::/16",  # 6to4 (embeds IPv4)
        "3fff::/20",  # documentation
        "5f00::/16",  # SRv6 SIDs
    )
)

_NAT64_WELL_KNOWN = ipaddress.ip_network("64:ff9b::/96")


def _embedded_ipv4(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | None:
    """Return the IPv4 address encoded in an IPv6 transition prefix.

    ``::ffff:a.b.c.d`` and the NAT64 well-known prefix ``64:ff9b::/96`` both
    carry an IPv4 address in their low 32 bits. Checking the embedded address
    is what stops ``64:ff9b::7f00:1`` from being treated as a public address.
    Some supported Python versions also report IPv4-mapped addresses as
    globally routable, so this applies to ``::ffff:`` too.
    """
    if not isinstance(addr, ipaddress.IPv6Address):
        return None
    if addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    if addr in _NAT64_WELL_KNOWN:
        return ipaddress.IPv4Address(int(addr) & 0xFFFFFFFF)
    return None


def is_blocked_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check whether an IP address is outside the globally routable space.

    This is an allowlist (``is_global``) plus explicit refusals for ranges
    that ``is_global`` reports as reachable but that must not be dialed:
    multicast, reserved, unspecified, link-local, loopback, IPv4-mapped and
    NAT64-encoded addresses (checked as the embedded IPv4 address), and the
    special-purpose transition/documentation ranges listed above.

    Args:
        addr: Parsed IP address.

    Returns:
        True if the address must not be connected to.
    """
    embedded = _embedded_ipv4(addr)
    if embedded is not None:
        addr = embedded

    if (
        addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
        or addr.is_link_local
        or addr.is_loopback
    ):
        return True
    if not addr.is_global:
        return True
    return any(
        addr in net for net in _SPECIAL_PURPOSE_NETWORKS if net.version == addr.version
    )


def is_global_host(hostname: str) -> bool:
    """Check whether a hostname resolves only to globally routable addresses.

    Callers use this to re-check each request the browser issues, including
    requests produced by a redirect, so that a public URL cannot bounce a
    navigation into loopback, an RFC1918 address, or the cloud metadata
    endpoint.

    Args:
        hostname: Hostname or IP literal taken from a request URL.

    Returns:
        True only if the host is an IP literal or resolves exclusively to
        public addresses. Returns False when resolution fails, so unresolvable
        hosts are refused rather than attempted.
    """
    host = (hostname or "").strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not host:
        return False

    try:
        return not is_blocked_ip(ipaddress.ip_address(host))
    except ValueError:
        pass  # Not an IP literal, resolve it below

    try:
        results = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        return False

    for _family, _type, _proto, _canonname, sockaddr in results:
        try:
            addr = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if is_blocked_ip(addr):
            return False

    return bool(results)
