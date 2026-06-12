"""CDP WebSocket proxy — expose browser CDP over a single port.

Handles WebSocket upgrade requests to ``/cdp`` and proxies CDP messages
between the external client and an internal Chromium CDP endpoint.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import struct
from collections.abc import Callable, Coroutine
from typing import Any

from veilrender.auth import verify_token
from veilrender._vendor.httpserver import Request

logger = logging.getLogger(__name__)

# WebSocket opcodes
_OP_TEXT = 0x1
_OP_BINARY = 0x2
_OP_CLOSE = 0x8
_OP_PING = 0x9
_OP_PONG = 0xA

_WS_MAGIC = b"258EAFA5-E914-47DA-95CA-5B0D11CF9245"


def _accept_key(key: str) -> str:
    """Compute Sec-WebSocket-Accept from Sec-WebSocket-Key."""
    digest = hashlib.sha1(key.encode() + _WS_MAGIC).digest()
    return base64.b64encode(digest).decode()


async def _read_ws_frame(
    reader: asyncio.StreamReader,
) -> tuple[int, bytes] | None:
    """Read one WebSocket frame. Returns (opcode, payload) or None on EOF."""
    try:
        head = await reader.readexactly(2)
    except (asyncio.IncompleteReadError, ConnectionError):
        return None

    opcode = head[0] & 0x0F
    masked = bool(head[1] & 0x80)
    length = head[1] & 0x7F

    if length == 126:
        raw = await reader.readexactly(2)
        length = struct.unpack("!H", raw)[0]
    elif length == 127:
        raw = await reader.readexactly(8)
        length = struct.unpack("!Q", raw)[0]

    if masked:
        mask = await reader.readexactly(4)
        data = bytearray(await reader.readexactly(length))
        for i in range(length):
            data[i] ^= mask[i % 4]
        return opcode, bytes(data)
    else:
        data = await reader.readexactly(length)
        return opcode, data


def _make_ws_frame(opcode: int, payload: bytes, mask: bool = False) -> bytes:
    """Build a WebSocket frame."""
    frame = bytearray()
    frame.append(0x80 | opcode)  # FIN + opcode

    length = len(payload)
    if length < 126:
        frame.append((0x80 if mask else 0) | length)
    elif length < 65536:
        frame.append((0x80 if mask else 0) | 126)
        frame.extend(struct.pack("!H", length))
    else:
        frame.append((0x80 if mask else 0) | 127)
        frame.extend(struct.pack("!Q", length))

    if mask:
        mask_key = os.urandom(4)
        frame.extend(mask_key)
        masked = bytearray(payload)
        for i in range(length):
            masked[i] ^= mask_key[i % 4]
        frame.extend(masked)
    else:
        frame.extend(payload)

    return bytes(frame)


async def _proxy_ws(
    src_reader: asyncio.StreamReader,
    dst_writer: asyncio.StreamWriter,
    *,
    src_masked: bool,
    dst_mask: bool,
    label: str,
) -> None:
    """Forward WebSocket frames from src to dst until close/EOF."""
    while True:
        result = await _read_ws_frame(src_reader)
        if result is None:
            break

        opcode, payload = result

        if opcode == _OP_CLOSE:
            frame = _make_ws_frame(_OP_CLOSE, payload, mask=dst_mask)
            dst_writer.write(frame)
            await dst_writer.drain()
            break
        elif opcode == _OP_PING:
            # Forward pings as-is to the other side
            frame = _make_ws_frame(_OP_PING, payload, mask=dst_mask)
            dst_writer.write(frame)
            await dst_writer.drain()
        else:
            frame = _make_ws_frame(opcode, payload, mask=dst_mask)
            dst_writer.write(frame)
            await dst_writer.drain()


def is_websocket_upgrade(method: str, headers: dict[str, str], path: str) -> bool:
    """Check if this HTTP request is a WebSocket upgrade to /cdp."""
    if not path.startswith("/cdp"):
        return False
    upgrade = headers.get("upgrade", "").lower()
    connection = headers.get("connection", "").lower()
    return method == "GET" and "websocket" in upgrade and "upgrade" in connection


async def handle_cdp_upgrade(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    headers: dict[str, str],
    path: str,
    query_string: str,
    get_cdp_url: Callable[[], Coroutine[Any, Any, str | None]],
) -> None:
    """Handle a WebSocket upgrade for CDP proxying.

    Args:
        reader: Client's stream reader.
        writer: Client's stream writer.
        headers: Parsed HTTP headers from the upgrade request.
        path: Request path.
        query_string: Raw query string.
        get_cdp_url: Async callable that returns the internal CDP WebSocket URL,
            or None if no browser is available.
    """
    # Auth check — build a minimal Request object for verify_token
    try:
        req = Request(
            method="GET",
            path=path,
            query_string=query_string,
            headers=headers,
            body=b"",
            client_addr=writer.get_extra_info("peername") or ("0.0.0.0", 0),
        )
        verify_token(req)
    except Exception:
        writer.write(b"HTTP/1.1 401 Unauthorized\r\n\r\n")
        await writer.drain()
        writer.close()
        return

    # Get WebSocket accept key
    ws_key = headers.get("sec-websocket-key", "")
    if not ws_key:
        writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\nMissing Sec-WebSocket-Key\r\n")
        await writer.drain()
        writer.close()
        return

    # Get internal CDP URL
    cdp_url = await get_cdp_url()
    if cdp_url is None:
        writer.write(
            b"HTTP/1.1 503 Service Unavailable\r\n\r\nNo browser available\r\n"
        )
        await writer.drain()
        writer.close()
        return

    # Connect to internal CDP
    # Parse ws://host:port/path from cdp_url
    from urllib.parse import urlparse

    parsed = urlparse(cdp_url)
    cdp_host = parsed.hostname or "127.0.0.1"
    cdp_port = parsed.port or 9222
    cdp_path = parsed.path or "/"

    try:
        cdp_reader, cdp_writer = await asyncio.open_connection(cdp_host, cdp_port)
    except Exception as exc:
        logger.error("Failed to connect to CDP at %s: %s", cdp_url, exc)
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        await writer.drain()
        writer.close()
        return

    # WebSocket handshake with internal CDP
    cdp_ws_key = base64.b64encode(os.urandom(16)).decode()
    ws_protocol = headers.get("sec-websocket-protocol", "")
    handshake = (
        f"GET {cdp_path} HTTP/1.1\r\n"
        f"Host: {cdp_host}:{cdp_port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
        f"Sec-WebSocket-Key: {cdp_ws_key}\r\n"
    )
    if ws_protocol:
        handshake += f"Sec-WebSocket-Protocol: {ws_protocol}\r\n"
    handshake += "\r\n"
    cdp_writer.write(handshake.encode())
    await cdp_writer.drain()

    # Read CDP handshake response
    cdp_response = b""
    while b"\r\n\r\n" not in cdp_response:
        chunk = await cdp_reader.read(4096)
        if not chunk:
            logger.error("CDP handshake failed: connection closed")
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            await writer.drain()
            writer.close()
            cdp_writer.close()
            return
        cdp_response += chunk

    if b"101" not in cdp_response.split(b"\r\n")[0]:
        logger.error("CDP handshake failed: %s", cdp_response[:200])
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        await writer.drain()
        writer.close()
        cdp_writer.close()
        return

    # Complete WebSocket handshake with the external client
    accept = _accept_key(ws_key)
    response = (
        f"HTTP/1.1 101 Switching Protocols\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
    )
    if ws_protocol:
        response += f"Sec-WebSocket-Protocol: {ws_protocol}\r\n"
    response += "\r\n"
    writer.write(response.encode())
    await writer.drain()

    logger.info("CDP proxy session started")

    # Bidirectional proxy
    try:
        await asyncio.gather(
            _proxy_ws(
                reader,
                cdp_writer,
                src_masked=True,
                dst_mask=True,
                label="client→cdp",
            ),
            _proxy_ws(
                cdp_reader,
                writer,
                src_masked=False,
                dst_mask=False,
                label="cdp→client",
            ),
        )
    except Exception as exc:
        logger.debug("CDP proxy ended: %s", exc)
    finally:
        logger.info("CDP proxy session ended")
        cdp_writer.close()
        writer.close()
