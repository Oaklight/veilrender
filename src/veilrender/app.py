"""VeilRender application entry point."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from veilrender._vendor.httpserver import App
from veilrender.browser import browser_manager
from veilrender.cdp_proxy import handle_cdp_upgrade, is_websocket_upgrade
from veilrender.config import settings
from veilrender.routes import health, render, screenshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> App:
    """Create and configure the VeilRender application."""
    app = App(max_body_size=10 * 1024 * 1024)  # 10 MB

    # Register routes
    health.register(app)
    render.register(app)
    screenshot.register(app)

    return app


def main() -> None:
    """Run the VeilRender server with HTTP + CDP WebSocket multiplexing."""
    app = create_app()

    async def run_server() -> None:
        await browser_manager.start()

        shutdown_event = asyncio.Event()

        async def handle_connection(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            """Multiplex: WebSocket upgrade to /cdp → CDP proxy, else → HTTP."""
            try:
                # Peek at the first request to decide routing
                raw = b""
                while b"\r\n\r\n" not in raw:
                    chunk = await asyncio.wait_for(reader.read(8192), timeout=30)
                    if not chunk:
                        writer.close()
                        return
                    raw += chunk

                # Parse the request line and headers
                header_block, _, body_start = raw.partition(b"\r\n\r\n")
                lines = header_block.decode("latin-1").split("\r\n")
                request_line = lines[0]
                parts = request_line.split(" ", 2)
                if len(parts) < 2:
                    writer.close()
                    return

                method = parts[0].upper()
                raw_path = parts[1]

                # Parse path and query string
                if "?" in raw_path:
                    path, query_string = raw_path.split("?", 1)
                else:
                    path, query_string = raw_path, ""

                # Parse headers
                headers: dict[str, str] = {}
                for line in lines[1:]:
                    if ":" in line:
                        key, _, value = line.partition(":")
                        headers[key.strip().lower()] = value.strip()

                # Check if this is a WebSocket upgrade to /cdp
                if is_websocket_upgrade(method, headers, path):
                    await handle_cdp_upgrade(
                        reader,
                        writer,
                        headers,
                        path,
                        query_string,
                        browser_manager.get_cdp_url,
                    )
                    return

                # Otherwise, delegate to httpserver
                # Re-feed the already-read data by creating a new reader
                combined_reader = asyncio.StreamReader()
                combined_reader.feed_data(raw)
                combined_reader.feed_eof()

                await app._handle_connection(combined_reader, writer)
            except Exception:
                logger.debug("Connection handler error", exc_info=True)
                try:
                    writer.close()
                except Exception:
                    pass

        server = await asyncio.start_server(
            handle_connection, settings.host, settings.port
        )
        addr = (
            server.sockets[0].getsockname()
            if server.sockets
            else (settings.host, settings.port)
        )
        logger.info(
            "VeilRender serving on %s:%d (auth=%s, cdp=ws://%s:%d/cdp)",
            addr[0],
            addr[1],
            "enabled" if settings.api_token else "disabled",
            addr[0],
            addr[1],
        )

        loop = asyncio.get_running_loop()
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, shutdown_event.set)

        try:
            async with server:
                await shutdown_event.wait()
        finally:
            await browser_manager.stop()

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass
