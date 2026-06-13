"""Playwright browser lifecycle management."""

from __future__ import annotations

import asyncio
import logging
import subprocess
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from cloakbrowser import ensure_binary, get_default_stealth_args
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from veilrender.config import settings

logger = logging.getLogger(__name__)

CDP_PORT = 9222


class BrowserManager:
    """Manages a shared Playwright browser instance.

    Launches Chromium directly (not via Playwright's launch()) so that
    ``--remote-debugging-port`` actually takes effect. Playwright then
    connects over CDP, and the CDP port is also available for external
    clients via the WebSocket proxy.
    """

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._chrome_proc: subprocess.Popen | None = None  # type: ignore[type-arg]
        self._semaphore = asyncio.Semaphore(settings.max_concurrent)
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Launch Chromium with CDP and connect Playwright to it."""
        executable_path = ensure_binary()
        stealth_args = get_default_stealth_args()

        chrome_args = [
            executable_path,
            "--headless",
            f"--remote-debugging-port={CDP_PORT}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            *stealth_args,
            "about:blank",
        ]

        self._chrome_proc = subprocess.Popen(
            chrome_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        # Wait for CDP to be ready
        cdp_url = f"http://127.0.0.1:{CDP_PORT}"
        for attempt in range(30):
            try:
                import urllib.request

                urllib.request.urlopen(f"{cdp_url}/json/version", timeout=1)
                break
            except Exception:
                await asyncio.sleep(0.5)
        else:
            stderr = (
                self._chrome_proc.stderr.read().decode()
                if self._chrome_proc.stderr
                else ""
            )
            raise RuntimeError(
                f"Chromium CDP not ready after 15s. stderr: {stderr[:500]}"
            )

        # Connect Playwright over CDP
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(
            f"http://127.0.0.1:{CDP_PORT}"
        )
        logger.info(
            "Browser started (CloakBrowser %s, CDP on :%d)", executable_path, CDP_PORT
        )

    async def get_cdp_url(self) -> str | None:
        """Return the internal CDP WebSocket URL, or None if unavailable."""
        await self._ensure_browser()
        try:
            import urllib.request
            import json

            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=2
            )
            data = json.loads(resp.read())
            ws_url = data.get("webSocketDebuggerUrl")
            if ws_url:
                return ws_url
        except Exception:
            logger.debug("Failed to get CDP WebSocket URL", exc_info=True)
        return f"ws://127.0.0.1:{CDP_PORT}"

    async def stop(self) -> None:
        """Close the browser, Playwright, and Chromium process."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        if self._chrome_proc:
            self._chrome_proc.terminate()
            try:
                self._chrome_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._chrome_proc.kill()
            self._chrome_proc = None
        logger.info("Browser stopped")

    async def _ensure_browser(self) -> Browser:
        """Restart browser if it crashed."""
        async with self._lock:
            chrome_dead = (
                self._chrome_proc is None or self._chrome_proc.poll() is not None
            )
            browser_dead = self._browser is None or not self._browser.is_connected()
            if chrome_dead or browser_dead:
                logger.warning("Browser not connected, restarting...")
                await self.stop()
                await self.start()
            assert self._browser is not None
            return self._browser

    @property
    def active_pages(self) -> int:
        """Number of browser pages currently in use."""
        return settings.max_concurrent - self._semaphore._value

    @property
    def is_browser_alive(self) -> bool:
        """Whether the browser process is connected."""
        return self._browser is not None and self._browser.is_connected()

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
