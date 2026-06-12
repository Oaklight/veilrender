"""VeilRender application entry point."""

from __future__ import annotations

import logging

from veilrender._vendor.httpserver import App
from veilrender.browser import browser_manager
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
    """Run the VeilRender server."""

    app = create_app()

    import asyncio

    async def run_server() -> None:
        await browser_manager.start()
        try:
            logger.info(
                "VeilRender starting on %s:%d (auth=%s)",
                settings.host,
                settings.port,
                "enabled" if settings.api_token else "disabled",
            )
            await app._serve(settings.host, settings.port)
        finally:
            await browser_manager.stop()

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass
