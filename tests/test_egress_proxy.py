"""Tests for the enforcing egress proxy.

The proxy is the enforcement point that sees redirect hops. These tests cover
the destination policy, CONNECT tunnels, plain-HTTP forwarding, upstream
chaining (HTTP and SOCKS5), and proxy authentication.
"""

from __future__ import annotations

import asyncio
import base64
import secrets
import socket
from urllib.parse import urlsplit

import pytest

from veilrender import egress_proxy
from veilrender.egress_proxy import (
    EgressPolicyError,
    EgressProxy,
    _select_global_addresses,
    _split_authority,
)

_DUMMY_PUBLIC = ("93.184.216.34", 443)


async def _start(handler) -> tuple[asyncio.Server, int]:
    """Start a TCP server on loopback and return it with its port."""
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    return server, port


async def _stop(server: asyncio.Server) -> None:
    server.close()
    await server.wait_closed()


async def _send(proxy: EgressProxy, payload: bytes) -> bytes:
    """Send a request to the proxy and read until it closes."""
    reader, writer = await asyncio.open_connection("127.0.0.1", proxy.port)
    try:
        writer.write(payload)
        await writer.drain()
        return await asyncio.wait_for(reader.read(), timeout=5)
    finally:
        writer.close()


def _status(response: bytes) -> bytes:
    return response.split(b"\r\n", 1)[0]


def _basic(credentials: str) -> bytes:
    """Encode a Basic proxy credential for a test request."""
    return base64.b64encode(credentials.encode()).decode().encode()


class TestAddressPolicy:
    def test_split_authority_with_port(self) -> None:
        assert _split_authority("example.com:8443", 443) == ("example.com", 8443)

    def test_split_authority_default_port(self) -> None:
        assert _split_authority("example.com", 443) == ("example.com", 443)

    def test_split_authority_ipv6(self) -> None:
        assert _split_authority("[2001:db8::1]:8443", 443) == (
            "2001:db8::1",
            8443,
        )

    def test_split_authority_rejects_unbracketed_ipv6(self) -> None:
        with pytest.raises(EgressPolicyError):
            _split_authority("2001:db8::1", 443)

    def test_split_authority_rejects_bad_port(self) -> None:
        with pytest.raises(EgressPolicyError):
            _split_authority("example.com:notaport", 443)

    def test_mixed_public_and_private_results_refused(self) -> None:
        infos = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 80)),
        ]
        with pytest.raises(EgressPolicyError):
            _select_global_addresses("mixed.test", infos)

    def test_private_only_results_refused(self) -> None:
        infos = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.10", 80)),
        ]
        with pytest.raises(EgressPolicyError):
            _select_global_addresses("internal.test", infos)

    def test_no_results_refused(self) -> None:
        with pytest.raises(EgressPolicyError):
            _select_global_addresses("empty.test", [])


class TestDestinationRefusals:
    def test_connect_to_loopback_refused(self) -> None:
        async def scenario() -> None:
            proxy = EgressProxy()
            await proxy.start()
            try:
                response = await _send(
                    proxy,
                    b"CONNECT 127.0.0.1:7860 HTTP/1.1\r\nHost: 127.0.0.1:7860\r\n\r\n",
                )
                assert b" 403 " in _status(response)
            finally:
                await proxy.stop()

        asyncio.run(scenario())

    def test_connect_to_ipv6_loopback_refused(self) -> None:
        async def scenario() -> None:
            proxy = EgressProxy()
            await proxy.start()
            try:
                response = await _send(
                    proxy, b"CONNECT [::1]:443 HTTP/1.1\r\nHost: [::1]:443\r\n\r\n"
                )
                assert b" 403 " in _status(response)
            finally:
                await proxy.stop()

        asyncio.run(scenario())

    def test_connect_to_ipv4_mapped_loopback_refused(self) -> None:
        async def scenario() -> None:
            proxy = EgressProxy()
            await proxy.start()
            try:
                response = await _send(
                    proxy,
                    b"CONNECT [::ffff:127.0.0.1]:443 HTTP/1.1\r\n"
                    b"Host: [::ffff:127.0.0.1]:443\r\n\r\n",
                )
                assert b" 403 " in _status(response)
            finally:
                await proxy.stop()

        asyncio.run(scenario())

    def test_absolute_form_private_refused(self) -> None:
        async def scenario() -> None:
            proxy = EgressProxy()
            await proxy.start()
            try:
                response = await _send(
                    proxy,
                    b"GET http://10.0.0.1/ HTTP/1.1\r\nHost: 10.0.0.1\r\n\r\n",
                )
                assert b" 403 " in _status(response)
            finally:
                await proxy.stop()

        asyncio.run(scenario())

    def test_absolute_form_metadata_refused(self) -> None:
        async def scenario() -> None:
            proxy = EgressProxy()
            await proxy.start()
            try:
                response = await _send(
                    proxy,
                    b"GET http://169.254.169.254/latest/meta-data/ HTTP/1.1\r\n"
                    b"Host: 169.254.169.254\r\n\r\n",
                )
                assert b" 403 " in _status(response)
            finally:
                await proxy.stop()

        asyncio.run(scenario())

    def test_origin_form_rejected(self) -> None:
        async def scenario() -> None:
            proxy = EgressProxy()
            await proxy.start()
            try:
                response = await _send(
                    proxy, b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n"
                )
                assert b" 400 " in _status(response)
            finally:
                await proxy.stop()

        asyncio.run(scenario())

    def test_https_absolute_form_rejected(self) -> None:
        async def scenario() -> None:
            proxy = EgressProxy()
            await proxy.start()
            try:
                response = await _send(
                    proxy,
                    b"GET https://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n",
                )
                assert b" 403 " in _status(response)
            finally:
                await proxy.stop()

        asyncio.run(scenario())


class TestForwarding:
    def test_absolute_form_forwarded_as_origin_form(self, monkeypatch) -> None:
        seen: dict[str, bytes] = {}
        holder = {"port": 0}

        async def origin(reader, writer) -> None:
            seen["head"] = await reader.readuntil(b"\r\n\r\n")
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n"
                b"Connection: close\r\n\r\nhello"
            )
            await writer.drain()
            writer.close()

        async def resolve(host: str, port: int) -> list:
            return [(socket.AF_INET, ("127.0.0.1", holder["port"]))]

        async def scenario() -> bytes:
            server, holder["port"] = await _start(origin)
            proxy = EgressProxy()
            await proxy.start()
            try:
                return await _send(
                    proxy,
                    b"GET http://public.test/hello?x=1 HTTP/1.1\r\n"
                    b"Host: public.test\r\n\r\n",
                )
            finally:
                await proxy.stop()
                await _stop(server)

        monkeypatch.setattr(egress_proxy, "_resolve_addresses", resolve)
        response = asyncio.run(scenario())
        assert b" 200 " in _status(response)
        assert response.endswith(b"hello")
        assert seen["head"].startswith(b"GET /hello?x=1 HTTP/1.1")

    def test_connect_tunnel_relays_bytes(self, monkeypatch) -> None:
        holder = {"port": 0}

        async def echo(reader, writer) -> None:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
            writer.close()

        async def resolve(host: str, port: int) -> list:
            return [(socket.AF_INET, ("127.0.0.1", holder["port"]))]

        async def scenario() -> bytes:
            server, holder["port"] = await _start(echo)
            proxy = EgressProxy()
            await proxy.start()
            reader, writer = await asyncio.open_connection("127.0.0.1", proxy.port)
            try:
                writer.write(
                    b"CONNECT public.test:443 HTTP/1.1\r\nHost: public.test:443\r\n\r\n"
                )
                await writer.drain()
                head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
                assert b" 200 " in head
                writer.write(b"ping")
                await writer.drain()
                return await asyncio.wait_for(reader.readexactly(4), timeout=5)
            finally:
                writer.close()
                await proxy.stop()
                await _stop(server)

        monkeypatch.setattr(egress_proxy, "_resolve_addresses", resolve)
        assert asyncio.run(scenario()) == b"ping"


class TestConfiguration:
    def test_playwright_proxy_disables_loopback_bypass(self) -> None:
        proxy = EgressProxy()
        config = proxy.playwright_proxy()
        assert config["server"] == "http://127.0.0.1:0"
        assert config["bypass"] == "<-loopback>"
        assert "username" not in config

    def test_playwright_proxy_carries_credentials(self) -> None:
        token = secrets.token_hex(12)
        proxy = EgressProxy(token=token)
        config = proxy.playwright_proxy()
        assert config["username"] == "veilrender"
        assert config["password"] == token

    def test_obscura_url_carries_credentials(self) -> None:
        token = secrets.token_hex(12)
        proxy = EgressProxy(token=token)
        assert proxy.obscura_proxy_url == f"http://veilrender:{token}@127.0.0.1:0"

    def test_advertised_loopback_detection(self) -> None:
        assert EgressProxy().advertised_host_is_loopback
        assert (
            EgressProxy(advertise="http://gateway:7870").advertised_host_is_loopback
            is False
        )


class TestAuthentication:
    def test_missing_credentials_challenged(self) -> None:
        async def scenario() -> bytes:
            proxy = EgressProxy(token=secrets.token_hex(12))
            await proxy.start()
            try:
                return await _send(
                    proxy,
                    b"CONNECT 127.0.0.1:443 HTTP/1.1\r\nHost: 127.0.0.1:443\r\n\r\n",
                )
            finally:
                await proxy.stop()

        response = asyncio.run(scenario())
        assert b" 407 " in _status(response)
        assert b"Proxy-Authenticate: Basic" in response

    def test_wrong_credentials_challenged(self) -> None:
        async def scenario() -> bytes:
            proxy = EgressProxy(token=secrets.token_hex(12))
            await proxy.start()
            try:
                header = _basic("veilrender:not-the-token")
                return await _send(
                    proxy,
                    b"CONNECT 127.0.0.1:443 HTTP/1.1\r\n"
                    b"Proxy-Authorization: Basic " + header + b"\r\n\r\n",
                )
            finally:
                await proxy.stop()

        assert b" 407 " in _status(asyncio.run(scenario()))

    def test_valid_credentials_reach_policy(self) -> None:
        async def scenario() -> bytes:
            token = secrets.token_hex(12)
            proxy = EgressProxy(token=token)
            await proxy.start()
            try:
                header = _basic(f"veilrender:{token}")
                return await _send(
                    proxy,
                    b"CONNECT 127.0.0.1:443 HTTP/1.1\r\n"
                    b"Proxy-Authorization: Basic " + header + b"\r\n\r\n",
                )
            finally:
                await proxy.stop()

        assert b" 403 " in _status(asyncio.run(scenario()))


class TestUpstreamChaining:
    def test_http_upstream_receives_connect_with_auth(self, monkeypatch) -> None:
        seen: list[bytes] = []
        holder = {"port": 0}

        async def upstream(reader, writer) -> None:
            seen.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
            writer.close()

        async def resolve(host: str, port: int) -> list:
            return [(socket.AF_INET, _DUMMY_PUBLIC)]

        async def scenario() -> bytes:
            server, holder["port"] = await _start(upstream)
            proxy = EgressProxy(
                upstream_url=f"http://user:pass@127.0.0.1:{holder['port']}"
            )
            await proxy.start()
            reader, writer = await asyncio.open_connection("127.0.0.1", proxy.port)
            try:
                writer.write(
                    b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"
                )
                await writer.drain()
                assert b" 200 " in await asyncio.wait_for(
                    reader.readuntil(b"\r\n\r\n"), timeout=5
                )
                writer.write(b"ping")
                await writer.drain()
                return await asyncio.wait_for(reader.readexactly(4), timeout=5)
            finally:
                writer.close()
                await proxy.stop()
                await _stop(server)

        monkeypatch.setattr(egress_proxy, "_resolve_addresses", resolve)
        assert asyncio.run(scenario()) == b"ping"
        head = seen[0]
        assert head.startswith(b"CONNECT example.com:443 HTTP/1.1")
        encoded = __import__("base64").b64encode(b"user:pass")
        assert b"Proxy-Authorization: Basic " + encoded in head

    def test_http_upstream_forces_connection_close(self, monkeypatch) -> None:
        seen: list[bytes] = []
        holder = {"port": 0}

        async def upstream(reader, writer) -> None:
            seen.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"
            )
            await writer.drain()
            writer.close()

        async def resolve(host: str, port: int) -> list:
            return [(socket.AF_INET, _DUMMY_PUBLIC)]

        async def scenario() -> bytes:
            server, holder["port"] = await _start(upstream)
            proxy = EgressProxy(upstream_url=f"http://127.0.0.1:{holder['port']}")
            await proxy.start()
            try:
                return await _send(
                    proxy,
                    b"GET http://example.com/x HTTP/1.1\r\n"
                    b"Host: example.com\r\nConnection: keep-alive\r\n\r\n",
                )
            finally:
                await proxy.stop()
                await _stop(server)

        monkeypatch.setattr(egress_proxy, "_resolve_addresses", resolve)
        response = asyncio.run(scenario())
        assert response.endswith(b"ok")
        lowered = seen[0].lower()
        assert seen[0].startswith(b"GET http://example.com/x HTTP/1.1")
        assert b"connection: close" in lowered
        assert lowered.count(b"connection:") == 1

    def test_socks5_upstream_handshake(self, monkeypatch) -> None:
        observed: dict[str, bytes] = {}
        holder = {"port": 0}

        async def socks(reader, writer) -> None:
            _ver, count = await reader.readexactly(2)
            await reader.readexactly(count)
            writer.write(b"\x05\x00")
            await writer.drain()
            ver, command, _rsv, atyp = await reader.readexactly(4)
            assert (ver, command) == (5, 1)
            if atyp == 3:
                length = (await reader.readexactly(1))[0]
                observed["host"] = await reader.readexactly(length)
            elif atyp == 1:
                observed["host"] = await reader.readexactly(4)
            await reader.readexactly(2)
            writer.write(
                b"\x05\x00\x00\x01" + socket.inet_aton(_DUMMY_PUBLIC[0]) + b"\x00\x00"
            )
            await writer.drain()
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
            writer.close()

        async def resolve(host: str, port: int) -> list:
            return [(socket.AF_INET, _DUMMY_PUBLIC)]

        async def scenario() -> bytes:
            server, holder["port"] = await _start(socks)
            proxy = EgressProxy(upstream_url=f"socks5://127.0.0.1:{holder['port']}")
            await proxy.start()
            reader, writer = await asyncio.open_connection("127.0.0.1", proxy.port)
            try:
                writer.write(
                    b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"
                )
                await writer.drain()
                assert b" 200 " in await asyncio.wait_for(
                    reader.readuntil(b"\r\n\r\n"), timeout=5
                )
                writer.write(b"ping")
                await writer.drain()
                return await asyncio.wait_for(reader.readexactly(4), timeout=5)
            finally:
                writer.close()
                await proxy.stop()
                await _stop(server)

        monkeypatch.setattr(egress_proxy, "_resolve_addresses", resolve)
        assert asyncio.run(scenario()) == b"ping"
        assert observed["host"] == b"example.com"

    def test_pinned_upstream_sends_validated_ip(self, monkeypatch) -> None:
        seen: list[bytes] = []
        holder = {"port": 0}

        async def upstream(reader, writer) -> None:
            seen.append(await reader.readuntil(b"\r\n\r\n"))
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            writer.close()

        async def resolve(host: str, port: int) -> list:
            return [(socket.AF_INET, _DUMMY_PUBLIC)]

        async def scenario() -> None:
            server, holder["port"] = await _start(upstream)
            proxy = EgressProxy(
                upstream_url=f"http://127.0.0.1:{holder['port']}",
                pin_upstream_ip=True,
            )
            await proxy.start()
            try:
                await _send(
                    proxy,
                    b"CONNECT example.com:443 HTTP/1.1\r\n"
                    b"Host: example.com:443\r\n\r\n",
                )
            finally:
                await proxy.stop()
                await _stop(server)

        monkeypatch.setattr(egress_proxy, "_resolve_addresses", resolve)
        asyncio.run(scenario())
        assert seen[0].startswith(b"CONNECT 93.184.216.34:443 HTTP/1.1")


class TestSpecialPurposeRanges:
    @pytest.mark.parametrize(
        "authority",
        [
            "224.0.0.1:80",  # multicast
            "239.255.255.250:80",  # SSDP multicast
            "[ff02::1]:443",  # IPv6 multicast
            "[64:ff9b::7f00:1]:443",  # NAT64 encoding of 127.0.0.1
            "[64:ff9b::a9fe:a9fe]:443",  # NAT64 encoding of metadata
            "[64:ff9b:1::1]:443",  # local-use NAT64
            "[2002:7f00:1::]:443",  # 6to4 encoding of 127.0.0.1
            "[2001::1]:443",  # Teredo
            "[5f00::1]:443",  # SRv6 SIDs
        ],
    )
    def test_special_purpose_destination_refused(self, authority: str) -> None:
        async def scenario() -> bytes:
            proxy = EgressProxy()
            await proxy.start()
            try:
                request = (
                    f"CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n\r\n"
                ).encode()
                return await _send(proxy, request)
            finally:
                await proxy.stop()

        assert b" 403 " in _status(asyncio.run(scenario()))


class TestRequestHardening:
    def test_control_characters_in_target_refused(self) -> None:
        async def scenario() -> bytes:
            proxy = EgressProxy()
            await proxy.start()
            try:
                return await _send(
                    proxy,
                    b"GET http://public.test/\x7f HTTP/1.1\r\n"
                    b"Host: public.test\r\n\r\n",
                )
            finally:
                await proxy.stop()

        assert b" 403 " in _status(asyncio.run(scenario()))

    def test_control_characters_in_authority_refused(self) -> None:
        async def scenario() -> bytes:
            proxy = EgressProxy()
            await proxy.start()
            try:
                return await _send(
                    proxy,
                    b"CONNECT public.test\t:443 HTTP/1.1\r\n\r\n",
                )
            finally:
                await proxy.stop()

        assert b" 403 " in _status(asyncio.run(scenario()))

    def test_port_zero_refused(self) -> None:
        async def scenario() -> bytes:
            proxy = EgressProxy()
            await proxy.start()
            try:
                return await _send(
                    proxy,
                    b"GET http://public.test:0/ HTTP/1.1\r\n"
                    b"Host: public.test:0\r\n\r\n",
                )
            finally:
                await proxy.stop()

        assert b" 403 " in _status(asyncio.run(scenario()))

    def test_origin_form_rejected_still(self) -> None:
        async def scenario() -> bytes:
            proxy = EgressProxy()
            await proxy.start()
            try:
                return await _send(
                    proxy, b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n"
                )
            finally:
                await proxy.stop()

        assert b" 400 " in _status(asyncio.run(scenario()))


class TestCanary:
    def test_http_canary_marks_its_token(self) -> None:
        async def scenario() -> tuple[bytes, int, bool]:
            proxy = EgressProxy()
            await proxy.start()
            url, token = proxy.canary_url()
            try:
                host = urlsplit(url).hostname
                response = await _send(
                    proxy,
                    f"GET {url} HTTP/1.1\r\nHost: {host}\r\n\r\n".encode(),
                )
                received = await proxy.wait_canary(token, timeout=0.5)
                return response, proxy.stats.canary_blocked, received
            finally:
                proxy.discard_canary(token)
                await proxy.stop()

        response, hits, received = asyncio.run(scenario())
        assert b" 403 " in _status(response)
        assert hits == 1
        assert received is True

    def test_connect_canary_marks_its_token(self) -> None:
        async def scenario() -> tuple[bytes, bool]:
            proxy = EgressProxy()
            await proxy.start()
            url, token = proxy.canary_url("https")
            try:
                host = urlsplit(url).hostname
                response = await _send(
                    proxy,
                    f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n".encode(),
                )
                received = await proxy.wait_canary(token, timeout=0.5)
                return response, received
            finally:
                proxy.discard_canary(token)
                await proxy.stop()

        response, received = asyncio.run(scenario())
        assert b" 403 " in _status(response)
        assert received is True

    def test_non_canary_block_not_counted(self) -> None:
        async def scenario() -> tuple[int, int]:
            proxy = EgressProxy()
            await proxy.start()
            try:
                await _send(
                    proxy,
                    b"GET http://192.0.2.1/normal HTTP/1.1\r\nHost: 192.0.2.1\r\n\r\n",
                )
                return proxy.stats.blocked, proxy.stats.canary_blocked
            finally:
                await proxy.stop()

        blocked, canary = asyncio.run(scenario())
        assert blocked == 1
        assert canary == 0
