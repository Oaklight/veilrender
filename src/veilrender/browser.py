"""Playwright browser lifecycle management."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from veilrender.config import settings

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages a shared Playwright browser instance.

    Uses a semaphore to limit concurrent browser contexts and provides
    a context manager for per-request page isolation.
    """

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._semaphore = asyncio.Semaphore(settings.max_concurrent)
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Launch the shared browser instance."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        logger.info("Browser started (pid=%s)", self._browser.contexts)

    async def stop(self) -> None:
        """Close the browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser stopped")

    async def _ensure_browser(self) -> Browser:
        """Restart browser if it crashed."""
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                logger.warning("Browser not connected, restarting...")
                await self.stop()
                await self.start()
            assert self._browser is not None
            return self._browser

    @asynccontextmanager
    async def get_page(
        self,
        *,
        viewport_width: int | None = None,
        viewport_height: int | None = None,
    ) -> AsyncIterator[tuple[BrowserContext, Page]]:
        """Create an isolated browser context and page.

        Yields:
            A (context, page) tuple. Both are closed automatically.
        """
        async with self._semaphore:
            browser = await self._ensure_browser()
            context: BrowserContext | None = None
            try:
                context = await browser.new_context(
                    viewport={
                        "width": viewport_width or settings.viewport_width,
                        "height": viewport_height or settings.viewport_height,
                    },
                    user_agent=None,  # use Playwright default
                )
                page = await context.new_page()
                yield context, page
            finally:
                if context:
                    await context.close()


browser_manager = BrowserManager()
