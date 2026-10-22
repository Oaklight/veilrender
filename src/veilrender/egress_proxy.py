"""Filtering egress proxy — the browser's only route to the network.

Every browser tier is pointed at this in-process HTTP proxy. The proxy sees
each connection the browser opens, including every redirect hop, which
Playwright route handlers cannot intercept. For each destination it:

1. resolves the hostname once and requires *every* returned address to be
   globally routable,
2. connects to one of those validated addresses rather than re-resolving, so a
   second DNS answer cannot move the connection to an internal host.

Traffic can optionally be chained through an operator-configured upstream
proxy (``VEILRENDER_UPSTREAM_PROXY``). The destination is still validated
locally, and the validated IP is sent upstream by default; forwarding the
hostname instead is an explicit opt-out (``VEILRENDER_UPSTREAM_PIN_IP=false``)
that lets the upstream resolve again.

The proxy is fail-closed: a destination that cannot be resolved, or that
resolves to any non-global address, is refused. If the proxy itself is
unreachable by a browser, that browser cannot make requests at all.
"""

from __future__ import annotations

import asyncio
import base64
import hmac
import ipaddress
import logging
import secrets
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit, urlunsplit

from veilrender.url_validator import is_blocked_ip

logger = logging.getLogger(__name__)

_MAX_HEADER_BYTES = 64 * 1024
_MAX_CONNECTIONS = 1024
_HEADER_TIMEOUT = 10.0
_CONNECT_TIMEOUT = 15.0
_DNS_TIMEOUT = 5.0
_DRAIN_TIMEOUT = 30.0
_IDLE_TIMEOUT = 300.0
_IO_CHUNK = 65536
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


class EgressPolicyError(Exception):
    """Raised when a destination is not allowed by the egress policy."""


class UpstreamError(Exception):
    """Raised when the configured upstream proxy cannot be used."""


@dataclass
class EgressStats:
    """Counters exposed through ``/metrics``."""

    requests: int = 0
    blocked: int = 0
    upstream_errors: int = 0
    bytes_up: int = 0
    bytes_down: int = 0
    canary_blocked: int = 0


@dataclass(frozen=True)
class UpstreamProxy:
    """Parsed upstream proxy URL."""

    scheme: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None

    @classmethod
    def parse(cls, url: str) -> UpstreamProxy:
        """Parse an upstream proxy URL.

        Args:
            url: Proxy URL, e.g. ``http://user:pass@proxy:3128`` or
                ``socks5://proxy:1080``.

        Returns:
            The parsed proxy.

        Raises:
            ValueError: If the URL is not a supported proxy URL.
        """
        parsed = urlsplit(url.strip())
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https", "socks5", "socks5h"):
            raise ValueError(
                f"Unsupported upstream proxy scheme '{scheme}' "
                "(expected http, https, socks5 or socks5h)"
            )
        if not parsed.hostname:
            raise ValueError("Upstream proxy URL has no host")
        default_ports = {"http": 8080, "https": 443, "socks5": 1080, "socks5h": 1080}
        try:
            port = parsed.port or default_ports[scheme]
        except ValueError as exc:
            raise ValueError(f"Invalid upstream proxy port: {exc}") from exc
        return cls(
            scheme="socks5" if scheme == "socks5h" else scheme,
            host=parsed.hostname,
            port=port,
            username=unquote(parsed.username) if parsed.username else None,
            password=unquote(parsed.password) if parsed.password else None,
        )

    def redacted(self) -> str:
        """Return a log-safe description without credentials."""
        return f"{self.scheme}://{self.host}:{self.port}"


def _has_control_chars(value: str) -> bool:
    """Return True if a request target contains C0 controls or DEL."""
    return any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def _has_forbidden_header_chars(value: str) -> bool:
    """Return True for control characters that must not appear in a header.

    Tab is a legal header value separator and is allowed; CR/LF cannot occur
    because headers are split on them. NUL and the remaining C0 controls must
    not be forwarded.
    """
    return any((ord(ch) < 0x20 and ch != "\t") or ord(ch) == 0x7F for ch in value)


def _split_authority(authority: str, default_port: int) -> tuple[str, int]:
    """Split a ``host:port`` authority, including bracketed IPv6 literals."""
    authority = authority.strip()
    if not authority:
        raise EgressPolicyError("Empty destination authority")
    if _has_control_chars(authority):
        raise EgressPolicyError("Control characters in destination authority")

    if authority.startswith("["):
        end = authority.find("]")
        if end == -1:
            raise EgressPolicyError("Malformed IPv6 authority")
        host = authority[1:end]
        rest = authority[end + 1 :]
        if rest and not rest.startswith(":"):
            raise EgressPolicyError("Malformed authority")
        port = default_port
        if rest:
            try:
                port = int(rest[1:])
            except ValueError as exc:
                raise EgressPolicyError("Malformed port") from exc
    else:
        host, sep, port_text = authority.rpartition(":")
        if not sep:
            host, port = authority, default_port
        else:
            if ":" in host:
                raise EgressPolicyError("IPv6 addresses must be bracketed")
            try:
                port = int(port_text)
            except ValueError as exc:
                raise EgressPolicyError("Malformed port") from exc

    if not host:
        raise EgressPolicyError("Empty destination host")
    if not 1 <= port <= 65535:
        raise EgressPolicyError(f"Port {port} out of range")
    return host, port


def _is_global_address(address: str) -> bool:
    """Return True only for an IP literal the destination policy allows."""
    try:
        addr = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not is_blocked_ip(addr)


def _select_global_addresses(host: str, infos: list[tuple]) -> list[tuple[int, tuple]]:
    """Validate ``getaddrinfo`` results and return connectable addresses.

    Every returned address must be globally routable. A host that resolves to
    a mix of public and private addresses is refused: the browser could
    otherwise land on the private one.

    Args:
        host: Hostname the results belong to (for error messages).
        infos: Results from ``getaddrinfo`` using ``SOCK_STREAM``.

    Returns:
        ``(family, sockaddr)`` pairs ready for ``asyncio.open_connection``.

    Raises:
        EgressPolicyError: If any address is non-global, or none were returned.
    """
    if not infos:
        raise EgressPolicyError(f"DNS returned no addresses for '{host}'")

    addresses: list[tuple[int, tuple]] = []
    for family, _type, _proto, _canonname, sockaddr in infos:
        ip = str(sockaddr[0])
        if not _is_global_address(ip):
            raise EgressPolicyError(f"'{host}' resolves to non-global address {ip}")
        addresses.append((family, sockaddr))
    return addresses


async def _resolve_addresses(host: str, port: int) -> list[tuple[int, tuple]]:
    """Resolve a hostname and return only validated global addresses."""
    host = host.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not _is_global_address(host):
            raise EgressPolicyError(f"IP address {host} is not globally routable")
        family = socket.AF_INET6 if literal.version == 6 else socket.AF_INET
        sockaddr: tuple = (
            (str(literal), port, 0, 0)
            if family == socket.AF_INET6
            else (str(literal), port)
        )
        return [(family, sockaddr)]

    try:
        infos = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(
                host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
            ),
            timeout=_DNS_TIMEOUT,
        )
    except asyncio.TimeoutError as exc:
        raise EgressPolicyError(f"DNS resolution timed out for '{host}'") from exc
    except (socket.gaierror, UnicodeError) as exc:
        raise EgressPolicyError(f"DNS resolution failed for '{host}': {exc}") from exc
    return _select_global_addresses(host, infos)


async def _open_validated(
    addresses: list[tuple[int, tuple]],
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Connect to the first reachable validated address."""
    last_exc: Exception | None = None
    for family, sockaddr in addresses:
        try:
            return await asyncio.wait_for(
                asyncio.open_connection(sockaddr[0], sockaddr[1], family=family),
                timeout=_CONNECT_TIMEOUT,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            last_exc = exc
    raise UpstreamError(f"Could not connect to destination: {last_exc}")


async def _read_header_block(reader: asyncio.StreamReader) -> tuple[bytes, bytes]:
    """Read an HTTP header block, returning it and any trailing bytes."""
    data = b""
    while True:
        chunk = await reader.read(8192)
        if not chunk:
            raise ConnectionError("connection closed before headers completed")
        data += chunk
        idx = data.find(b"\r\n\r\n")
        if idx != -1:
            return data[:idx], data[idx + 4 :]
        if len(data) > _MAX_HEADER_BYTES:
            raise EgressPolicyError("request headers too large")


async def _drain(writer: asyncio.StreamWriter, timeout: float = _DRAIN_TIMEOUT) -> None:
    """Flush a writer without waiting forever for a non-reading peer."""
    await asyncio.wait_for(writer.drain(), timeout=timeout)


def _header_value(headers: list[bytes], name: bytes) -> bytes | None:
    """Return the first value of a header (case-insensitive)."""
    lowered = name.lower()
    for line in headers:
        key, sep, value = line.partition(b":")
        if sep and key.strip().lower() == lowered:
            return value.strip()
    return None


def _format_authority(host: str, port: int | None) -> str:
    """Format a ``host:port`` authority, bracketing IPv6 literals."""
    host_part = f"[{host}]" if ":" in host else host
    return f"{host_part}:{port}" if port is not None else host_part


def _absolute_url(host: str, port: int | None, path: str, query: str) -> str:
    """Build an absolute-form HTTP request target from validated parts."""
    return urlunsplit(("http", _format_authority(host, port), path or "/", query, ""))


def _rebuild_head(
    headers: list[bytes],
    request_line: str,
    extra: list[str] | None = None,
    *,
    force_close: bool = False,
) -> bytes:
    """Rebuild a request head, dropping proxy-only headers.

    ``force_close`` is used when relaying plain HTTP through an upstream
    proxy. A kept-alive connection to a proxy can carry a request for a
    different destination without another policy check, so each connection is
    limited to the one destination that was validated.
    """
    drop = {b"proxy-authorization", b"proxy-connection"}
    if force_close:
        drop.add(b"connection")
    out = [request_line]
    for line in headers:
        key = line.split(b":", 1)[0].strip().lower()
        if key in drop:
            continue
        text = line.decode("latin-1")
        if _has_forbidden_header_chars(text):
            raise EgressPolicyError("Control characters in request header")
        out.append(text)
    if force_close:
        out.append("Connection: close")
    if extra:
        out.extend(extra)
    return ("\r\n".join(out) + "\r\n\r\n").encode("latin-1")


class EgressProxy:
    """In-process filtering HTTP proxy.

    Supports the proxy protocol browsers speak: ``CONNECT`` tunnels for
    HTTPS/WSS, and absolute-form requests for plain HTTP. With an upstream
    proxy configured, validated traffic is chained through it.
    """

    def __init__(
        self,
        *,
        bind_host: str = "127.0.0.1",
        port: int = 0,
        advertise: str = "",
        upstream_url: str = "",
        pin_upstream_ip: bool = False,
        token: str | None = None,
    ) -> None:
        self.bind_host = bind_host
        self._port = port
        self.advertise = advertise.strip()
        self.upstream = UpstreamProxy.parse(upstream_url) if upstream_url else None
        self.pin_upstream_ip = pin_upstream_ip
        self.token = token
        self.stats = EgressStats()
        self._server: asyncio.Server | None = None
        self._active_connections = 0
        self._canary_events: dict[str, asyncio.Event] = {}

    @classmethod
    def from_settings(cls) -> EgressProxy:
        """Build the proxy from ``VEILRENDER_*`` settings."""
        from veilrender.config import settings

        proxy = cls(
            bind_host=settings.egress_bind,
            port=settings.egress_port,
            advertise=settings.egress_advertise,
            upstream_url=settings.upstream_proxy,
            pin_upstream_ip=settings.upstream_pin_ip,
            token=settings.egress_token,
        )
        if not proxy._bind_is_loopback() and not proxy.token:
            raise ValueError(
                "VEILRENDER_EGRESS_BIND is not a loopback address but "
                "VEILRENDER_EGRESS_PROXY_TOKEN is unset; refusing to expose an "
                "unauthenticated proxy on the network"
            )
        return proxy

    @property
    def advertised_host_is_loopback(self) -> bool:
        """Whether the URL given to browsers points at loopback."""
        host = urlsplit(self.server_url).hostname or ""
        if host in _LOOPBACK_HOSTS:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def _bind_is_loopback(self) -> bool:
        host = self.bind_host.strip().lower()
        if host in _LOOPBACK_HOSTS:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    @property
    def port(self) -> int:
        """Actual listening port (resolved after ``start``)."""
        return self._port

    @property
    def server_url(self) -> str:
        """URL browsers should use to reach this proxy."""
        if self.advertise:
            if "://" not in self.advertise:
                return f"http://{self.advertise}"
            return self.advertise
        host = self.bind_host
        if host in ("0.0.0.0", "::", ""):
            host = "127.0.0.1"
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}:{self._port}"

    def _server_url_with_credentials(self) -> str:
        """Server URL with Basic credentials embedded (used by Obscura)."""
        if not self.token:
            return self.server_url
        parsed = urlsplit(self.server_url)
        credentials = f"veilrender:{self.token}@"
        return urlunsplit(parsed._replace(netloc=credentials + parsed.netloc))

    def playwright_proxy(self) -> dict[str, str]:
        """Proxy configuration for ``browser.new_context(proxy=...)``.

        ``<-loopback>`` disables Chromium's implicit proxy bypass for
        localhost. Without it a navigation to a loopback address would skip
        the proxy (and its policy) entirely.
        """
        config = {"server": self.server_url, "bypass": "<-loopback>"}
        if self.token:
            config["username"] = "veilrender"
            config["password"] = self.token
        return config

    @property
    def obscura_proxy_url(self) -> str:
        """Value for Obscura's ``--proxy`` flag."""
        return self._server_url_with_credentials()

    @property
    def active_connections(self) -> int:
        """Number of client connections currently being handled."""
        return self._active_connections

    def canary_url(self, scheme: str = "http") -> tuple[str, str]:
        """Register a canary and return its URL and token.

        The hostname is guaranteed not to resolve (``.invalid``), so a request
        arriving here was sent to the proxy rather than resolved and dialed by
        the browser. The request is refused on receipt and marks this token's
        event, which lets a caller attest that a specific navigation used the
        proxy. Tokens are single-use and removed by ``discard_canary``.
        """
        token = secrets.token_hex(8)
        self._canary_events[token] = asyncio.Event()
        return f"{scheme}://canary-{token}.invalid/", token

    def _mark_canary(self, target: str) -> bool:
        """Mark the canary token contained in a request target as received."""
        for token, event in self._canary_events.items():
            if token in target:
                event.set()
                return True
        return False

    async def wait_canary(self, token: str, timeout: float = 2.0) -> bool:
        """Wait for a specific canary request to arrive through the proxy."""
        event = self._canary_events.get(token)
        if event is None:
            return False
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def discard_canary(self, token: str) -> None:
        """Forget a canary token after it has been waited for."""
        self._canary_events.pop(token, None)

    async def start(self) -> None:
        """Bind the listening socket."""
        self._server = await asyncio.start_server(
            self._handle_client, self.bind_host, self._port
        )
        sockets = self._server.sockets or []
        if sockets:
            self._port = sockets[0].getsockname()[1]
        upstream = self.upstream.redacted() if self.upstream else "direct"
        logger.info(
            "Egress proxy listening on %s (upstream=%s, auth=%s)",
            self.server_url,
            upstream,
            "enabled" if self.token else "disabled",
        )

    async def stop(self) -> None:
        """Close the listener and wait for it to finish."""
        if self._server is not None:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:
                pass
            self._server = None

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle one client connection."""
        if self._active_connections >= _MAX_CONNECTIONS:
            await self._respond(
                writer, 503, "Service Unavailable", "Too many proxy connections"
            )
            try:
                writer.close()
            except Exception:
                pass
            return

        self._active_connections += 1
        upstream_writer: asyncio.StreamWriter | None = None
        try:
            try:
                head, rest = await asyncio.wait_for(
                    _read_header_block(reader), timeout=_HEADER_TIMEOUT
                )
            except asyncio.TimeoutError:
                await self._respond(
                    writer, 408, "Request Timeout", "Request header timeout"
                )
                return

            lines = head.split(b"\r\n")
            request_line = lines[0].decode("latin-1")
            parts = request_line.split(" ")
            if len(parts) != 3:
                await self._respond(writer, 400, "Bad Request", "Malformed request")
                return
            method, target, version = parts
            headers = lines[1:]
            self.stats.requests += 1

            if _has_control_chars(target):
                raise EgressPolicyError("Control characters in request target")
            if self._mark_canary(target):
                # Canary requests are refused on receipt, before DNS, so the
                # attestation works regardless of how .invalid is resolved.
                self.stats.canary_blocked += 1
                logger.debug("Egress canary received")
                await self._respond(
                    writer,
                    403,
                    "Forbidden",
                    "Destination blocked by outbound request policy",
                )
                return

            if not self._authorized(headers):
                await self._respond(
                    writer,
                    407,
                    "Proxy Authentication Required",
                    "Proxy authentication required",
                    extra_headers=['Proxy-Authenticate: Basic realm="veilrender"'],
                )
                return

            if method.upper() == "CONNECT":
                upstream_writer = await self._handle_connect(
                    reader, writer, target, rest
                )
            elif "://" in target:
                upstream_writer = await self._handle_absolute(
                    reader, writer, method, target, version, headers, rest
                )
            else:
                await self._respond(
                    writer,
                    400,
                    "Bad Request",
                    "This endpoint is an HTTP proxy; requests must use "
                    "absolute-form or CONNECT",
                )
        except EgressPolicyError as exc:
            self.stats.blocked += 1
            logger.warning("Egress policy blocked request: %s", exc)
            await self._respond(
                writer,
                403,
                "Forbidden",
                "Destination blocked by outbound request policy",
            )
        except UpstreamError as exc:
            self.stats.upstream_errors += 1
            logger.warning("Egress request failed: %s", exc)
            await self._respond(writer, 502, "Bad Gateway", "Upstream request failed")
        except (ConnectionError, asyncio.IncompleteReadError, OSError) as exc:
            logger.debug("Egress client connection closed: %s", exc)
        except Exception:
            logger.warning("Egress proxy error", exc_info=True)
        finally:
            self._active_connections -= 1
            if upstream_writer is not None:
                try:
                    upstream_writer.close()
                except Exception:
                    pass
            try:
                writer.close()
            except Exception:
                pass

    def _authorized(self, headers: list[bytes]) -> bool:
        """Check Proxy-Authorization when a token is configured."""
        if not self.token:
            return True
        value = _header_value(headers, b"proxy-authorization")
        if not value:
            return False
        scheme, _, credentials = value.partition(b" ")
        if scheme.lower() != b"basic":
            return False
        try:
            decoded = base64.b64decode(credentials, validate=True).decode("utf-8")
        except Exception:
            return False
        return hmac.compare_digest(decoded, f"veilrender:{self.token}")

    async def _handle_connect(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        authority: str,
        rest: bytes,
    ) -> asyncio.StreamWriter:
        """Open a CONNECT tunnel and relay it until either side closes."""
        host, port = _split_authority(authority, 443)
        addresses = await _resolve_addresses(host, port)

        initial = b""
        if self.upstream is not None:
            up_reader, up_writer, initial = await self._connect_upstream(
                host, port, addresses
            )
        else:
            up_reader, up_writer = await _open_validated(addresses)

        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n" + initial)
        await _drain(writer)
        if rest:
            up_writer.write(rest)
            await _drain(up_writer)
        await self._tunnel(reader, writer, up_reader, up_writer)
        return up_writer

    async def _handle_absolute(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        method: str,
        target: str,
        version: str,
        headers: list[bytes],
        rest: bytes,
    ) -> asyncio.StreamWriter:
        """Relay a plain-HTTP absolute-form request."""
        parsed = urlsplit(target)
        if parsed.scheme.lower() != "http":
            raise EgressPolicyError(
                f"Scheme '{parsed.scheme}' must use CONNECT, not absolute-form"
            )
        if parsed.username or parsed.password:
            raise EgressPolicyError("Credentials in the request URL are not allowed")
        host = parsed.hostname
        if not host:
            raise EgressPolicyError("Missing hostname")
        try:
            port = parsed.port
        except ValueError as exc:
            raise EgressPolicyError(f"Invalid port: {exc}") from exc
        if port is None:
            port = 80
        elif port == 0:
            raise EgressPolicyError("Port 0 is not a valid destination")
        if _has_control_chars(host):
            raise EgressPolicyError("Control characters in destination host")

        addresses = await _resolve_addresses(host, port)
        origin_target = parsed.path or "/"
        if parsed.query:
            origin_target = f"{origin_target}?{parsed.query}"

        if self.upstream is not None and self.upstream.scheme == "socks5":
            up_reader, up_writer = await self._connect_via_socks(host, port, addresses)
            request_line = f"{method} {origin_target} {version}"
            extra: list[str] = []
            force_close = False
        elif self.upstream is not None:
            up_reader, up_writer = await self._connect_http_upstream()
            fwd_host = str(addresses[0][1][0]) if self.pin_upstream_ip else host
            fwd_target = _absolute_url(fwd_host, parsed.port, parsed.path, parsed.query)
            request_line = f"{method} {fwd_target} {version}"
            extra = self._upstream_auth_headers()
            # A pooled connection to an HTTP proxy could carry a request for
            # another destination; one connection, one validated target.
            force_close = True
        else:
            up_reader, up_writer = await _open_validated(addresses)
            request_line = f"{method} {origin_target} {version}"
            extra = []
            force_close = False

        up_writer.write(
            _rebuild_head(headers, request_line, extra, force_close=force_close) + rest
        )
        await _drain(up_writer)
        await self._tunnel(reader, writer, up_reader, up_writer)
        return up_writer

    # ------------------------------------------------------------------
    # Upstream connections
    # ------------------------------------------------------------------

    def _upstream_auth_headers(self) -> list[str]:
        """Build a Proxy-Authorization header for the upstream."""
        if self.upstream is None or self.upstream.username is None:
            return []
        raw = f"{self.upstream.username}:{self.upstream.password or ''}"
        encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
        return [f"Proxy-Authorization: Basic {encoded}"]

    async def _connect_http_upstream(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open a TCP (or TLS) connection to an HTTP(S) upstream proxy."""
        assert self.upstream is not None
        ssl_context: ssl.SSLContext | None = None
        server_hostname: str | None = None
        if self.upstream.scheme == "https":
            ssl_context = ssl.create_default_context()
            server_hostname = self.upstream.host
        try:
            return await asyncio.wait_for(
                asyncio.open_connection(
                    self.upstream.host,
                    self.upstream.port,
                    ssl=ssl_context,
                    server_hostname=server_hostname,
                ),
                timeout=_CONNECT_TIMEOUT,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            raise UpstreamError(f"Upstream proxy unreachable: {exc}") from exc

    async def _connect_upstream(
        self, host: str, port: int, addresses: list[tuple[int, tuple]]
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, bytes]:
        """Open a tunnel through the configured upstream proxy.

        Returns:
            The upstream reader and writer, plus any bytes the upstream sent
            after its CONNECT response (they belong to the tunnel).
        """
        assert self.upstream is not None
        if self.upstream.scheme == "socks5":
            reader, writer = await self._connect_via_socks(host, port, addresses)
            return reader, writer, b""

        up_reader, up_writer = await self._connect_http_upstream()
        connect_host = (
            self._pinned_host(host, addresses) if self.pin_upstream_ip else host
        )
        authority = _format_authority(connect_host, port)
        lines = [
            f"CONNECT {authority} HTTP/1.1",
            f"Host: {authority}",
            *self._upstream_auth_headers(),
        ]
        up_writer.write(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))
        await _drain(up_writer)

        try:
            reply, rest = await asyncio.wait_for(
                _read_header_block(up_reader), timeout=_CONNECT_TIMEOUT
            )
        except (ConnectionError, asyncio.TimeoutError, EgressPolicyError) as exc:
            up_writer.close()
            raise UpstreamError(
                f"Upstream proxy did not answer CONNECT: {exc}"
            ) from exc

        status_line = reply.split(b"\r\n", 1)[0].decode("latin-1")
        parts = status_line.split(" ")
        if len(parts) < 2 or parts[1] != "200":
            up_writer.close()
            raise UpstreamError(f"Upstream proxy refused CONNECT: {status_line}")
        return up_reader, up_writer, rest

    async def _connect_via_socks(
        self, host: str, port: int, addresses: list[tuple[int, tuple]]
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open a tunnel through a SOCKS5 upstream."""
        assert self.upstream is not None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.upstream.host, self.upstream.port),
                timeout=_CONNECT_TIMEOUT,
            )
        except (OSError, asyncio.TimeoutError) as exc:
            raise UpstreamError(f"SOCKS5 proxy unreachable: {exc}") from exc

        try:
            await self._socks5_handshake(reader, writer, host, port, addresses)
        except Exception:
            writer.close()
            raise
        return reader, writer

    async def _socks5_handshake(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
        addresses: list[tuple[int, tuple]],
    ) -> None:
        """Perform a SOCKS5 CONNECT handshake."""
        assert self.upstream is not None
        use_auth = self.upstream.username is not None
        methods = b"\x05\x02\x00\x02" if use_auth else b"\x05\x01\x00"
        writer.write(methods)
        await _drain(writer)
        reply = await asyncio.wait_for(reader.readexactly(2), timeout=_CONNECT_TIMEOUT)
        if reply[0] != 0x05 or reply[1] == 0xFF:
            raise UpstreamError("SOCKS5 proxy rejected authentication methods")
        if reply[1] == 0x02:
            if not use_auth:
                raise UpstreamError("SOCKS5 proxy requires authentication")
            username = (self.upstream.username or "").encode("utf-8")
            password = (self.upstream.password or "").encode("utf-8")
            writer.write(
                b"\x01"
                + bytes([len(username)])
                + username
                + bytes([len(password)])
                + password
            )
            await _drain(writer)
            auth_reply = await asyncio.wait_for(
                reader.readexactly(2), timeout=_CONNECT_TIMEOUT
            )
            if auth_reply[1] != 0x00:
                raise UpstreamError("SOCKS5 authentication failed")
        elif reply[1] != 0x00:
            raise UpstreamError("SOCKS5 proxy selected an unsupported auth method")

        target = self._pinned_host(host, addresses) if self.pin_upstream_ip else host
        try:
            literal = ipaddress.ip_address(target)
        except ValueError:
            encoded = host.encode("idna")
            address_field = b"\x03" + bytes([len(encoded)]) + encoded
        else:
            packed = literal.packed
            address_field = (b"\x01" if len(packed) == 4 else b"\x04") + packed

        writer.write(b"\x05\x01\x00" + address_field + port.to_bytes(2, "big"))
        await _drain(writer)
        reply = await asyncio.wait_for(reader.readexactly(4), timeout=_CONNECT_TIMEOUT)
        if reply[0] != 0x05 or reply[1] != 0x00:
            raise UpstreamError(f"SOCKS5 CONNECT failed (code {reply[1]})")
        atyp = reply[3]
        if atyp == 0x01:
            await reader.readexactly(4 + 2)
        elif atyp == 0x04:
            await reader.readexactly(16 + 2)
        elif atyp == 0x03:
            length = (await reader.readexactly(1))[0]
            await reader.readexactly(length + 2)
        else:
            raise UpstreamError("SOCKS5 proxy sent an invalid address type")

    @staticmethod
    def _pinned_host(host: str, addresses: list[tuple[int, tuple]]) -> str:
        """Return the validated IP literal for upstream IP pinning."""
        return str(addresses[0][1][0])

    # ------------------------------------------------------------------
    # Relay and responses
    # ------------------------------------------------------------------

    async def _tunnel(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream_reader: asyncio.StreamReader,
        upstream_writer: asyncio.StreamWriter,
    ) -> None:
        """Relay bytes in both directions until either side closes."""

        async def pump(
            source: asyncio.StreamReader,
            destination: asyncio.StreamWriter,
            *,
            is_upload: bool,
        ) -> None:
            try:
                while True:
                    try:
                        chunk = await asyncio.wait_for(
                            source.read(_IO_CHUNK), timeout=_IDLE_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        break
                    if not chunk:
                        break
                    destination.write(chunk)
                    await _drain(destination)
                    if is_upload:
                        self.stats.bytes_up += len(chunk)
                    else:
                        self.stats.bytes_down += len(chunk)
            except (
                ConnectionError,
                OSError,
                asyncio.IncompleteReadError,
                asyncio.TimeoutError,
            ):
                pass
            finally:
                try:
                    destination.write_eof()
                except (RuntimeError, OSError):
                    pass

        up_task = asyncio.create_task(
            pump(client_reader, upstream_writer, is_upload=True)
        )
        down_task = asyncio.create_task(
            pump(upstream_reader, client_writer, is_upload=False)
        )
        _done, pending = await asyncio.wait(
            {up_task, down_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    @staticmethod
    async def _respond(
        writer: asyncio.StreamWriter,
        status: int,
        reason: str,
        message: str,
        *,
        extra_headers: list[str] | None = None,
    ) -> None:
        """Write a small plain-text response and close."""
        body = message.encode("utf-8", "replace")
        headers = [
            f"HTTP/1.1 {status} {reason}",
            "Content-Type: text/plain; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Connection: close",
        ]
        if extra_headers:
            headers.extend(extra_headers)
        writer.write(("\r\n".join(headers) + "\r\n\r\n").encode("latin-1") + body)
        try:
            await _drain(writer)
        except (ConnectionError, OSError, asyncio.TimeoutError):
            pass
