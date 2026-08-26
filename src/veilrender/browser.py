"""Browser lifecycle management.

Supports a single local browser (default) or a pool of remote workers
via CDP (Chromium) or Playwright protocol (Firefox/Camoufox).
"""

from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
import random
import subprocess
import urllib.request
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from patchright.async_api import Browser, BrowserContext, Page, async_playwright

from veilrender.config import settings
from veilrender.filters import load_blocklist, make_route_handler

logger = logging.getLogger(__name__)

CDP_PORT = 9222

_CLOAKBROWSER_DEFAULT_DIR = os.path.expanduser("~/.cloakbrowser")


_CLOAKBROWSER_PYPI_URL = "https://pypi.org/pypi/cloakbrowser/json"


def _resolve_chromium_version() -> str:
    """Resolve CloakBrowser's Chromium version from the PyPI wheel."""
    import re
    import zipfile
    from io import BytesIO

    pypi = _fetch_json(_CLOAKBROWSER_PYPI_URL, timeout=30)
    whl_url = next(u["url"] for u in pypi["urls"] if u["filename"].endswith(".whl"))
    whl_data = urllib.request.urlopen(whl_url, timeout=60).read()
    with zipfile.ZipFile(BytesIO(whl_data)) as zf:
        for name in zf.namelist():
            if name.endswith("config.py"):
                content = zf.read(name).decode()
                m = re.search(r'CHROMIUM_VERSION\s*=\s*"([^"]+)"', content)
                if m:
                    return m.group(1)
    raise RuntimeError("Could not resolve CloakBrowser Chromium version")


def _detect_platform() -> str:
    """Detect platform string for CloakBrowser download URL."""
    import platform as _platform

    machine = _platform.machine().lower()
    system = _platform.system().lower()
    if system == "linux":
        arch = "x64" if machine in ("x86_64", "amd64") else "arm64"
        return f"linux-{arch}"
    if system == "darwin":
        arch = "arm64" if machine == "arm64" else "x64"
        return f"mac-{arch}"
    raise RuntimeError(f"Unsupported platform: {system}-{machine}")


def _download_browser_binary() -> str:
    """Download CloakBrowser binary from cloakbrowser.dev (or mirror)."""
    import tarfile

    version = _resolve_chromium_version()
    plat = _detect_platform()
    gh_url = f"https://github.com/CloakHQ/cloakbrowser/releases/download/chromium-v{version}/cloakbrowser-{plat}.tar.gz"
    mirror = os.environ.get("CLOAKBROWSER_MIRROR", "")
    url = f"{mirror}/{gh_url}" if mirror else gh_url
    dest_dir = os.path.join(_CLOAKBROWSER_DEFAULT_DIR, f"chromium-{version}")
    binary = os.path.join(dest_dir, "chrome")

    if os.path.isfile(binary):
        logger.info("Binary already exists at %s", binary)
        return binary

    logger.info("Downloading CloakBrowser %s (%s)...", version, plat)
    os.makedirs(dest_dir, exist_ok=True)
    tmp = os.path.join(dest_dir, ".download.tar.gz")
    try:
        urllib.request.urlretrieve(url, tmp)
        with tarfile.open(tmp, "r:gz") as tf:
            tf.extractall(dest_dir)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

    if os.path.isfile(binary):
        os.chmod(binary, 0o755)
    logger.info("Downloaded CloakBrowser %s to %s", version, binary)
    return binary


def _find_browser_binary() -> str:
    """Locate a CloakBrowser (or compatible) Chromium binary.

    Search order:
    1. CLOAKBROWSER_BINARY env var
    2. ~/.cloakbrowser/*/chrome (pre-downloaded or Docker-installed)
    3. Auto-download from cloakbrowser.dev
    """
    env_path = os.environ.get("CLOAKBROWSER_BINARY")
    if env_path:
        if os.path.isfile(env_path) and os.access(env_path, os.X_OK):
            logger.info("Using browser binary from CLOAKBROWSER_BINARY: %s", env_path)
            return env_path
        raise FileNotFoundError(
            f"CLOAKBROWSER_BINARY={env_path} not found or not executable"
        )

    candidates = sorted(
        glob.glob(f"{_CLOAKBROWSER_DEFAULT_DIR}/*/chrome"), reverse=True
    )
    if candidates:
        logger.info("Found browser binary: %s", candidates[0])
        return candidates[0]

    return _download_browser_binary()


def _get_stealth_args() -> list[str]:
    """Get stealth launch arguments for CloakBrowser."""
    fingerprint = random.randint(10000, 99999)
    return [
        "--no-sandbox",
        f"--fingerprint={fingerprint}",
        "--fingerprint-platform=linux",
    ]


def _fetch_json(url: str, timeout: int = 2) -> Any:
    """Fetch and parse JSON from a URL (blocking)."""
    resp = urllib.request.urlopen(url, timeout=timeout)
    return json.loads(resp.read())


def _count_cdp_pages(http_base: str, timeout: int = 2) -> int:
    """Count open page targets via CDP /json endpoint."""
    try:
        targets = _fetch_json(f"{http_base}/json", timeout)
        if isinstance(targets, list):
            return sum(1 for t in targets if t.get("type") == "page")
    except Exception:
        pass
    return -1


def _ws_to_http(endpoint: str) -> str:
    """Convert a ws(s):// URL to http(s):// for CDP HTTP API."""
    if endpoint.startswith("wss://"):
        return "https://" + endpoint[6:]
    if endpoint.startswith("ws://"):
        return "http://" + endpoint[5:]
    return endpoint


def _resolve_to_ip(endpoint: str) -> str:
    """Replace hostname with IP in a CDP endpoint URL.

    Chromium's CDP HTTP API rejects Host headers that aren't IP
    addresses or ``localhost``. This resolves the hostname to an IP
    so connections from Docker containers (where the Host header
    would be e.g. ``browser-worker:9222``) work correctly.
    """
    import socket
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(endpoint)
    host = parsed.hostname
    if not host or host in ("localhost", "127.0.0.1", "::1"):
        return endpoint
    try:
        float(host.replace(".", "").replace(":", ""))
        return endpoint
    except ValueError:
        pass
    try:
        ip = socket.gethostbyname(host)
        new_netloc = f"{ip}:{parsed.port}" if parsed.port else ip
        return urlunparse(parsed._replace(netloc=new_netloc))
    except socket.gaierror:
        return endpoint


# ---------------------------------------------------------------------------
# Worker base interface
# ---------------------------------------------------------------------------


class _BaseWorker:
    """Common interface for local and remote browser workers."""

    endpoint: str = "unknown"
    worker_type: str = "unknown"

    def __init__(self, max_concurrent: int) -> None:
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.healthy = False

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def ensure_ready(self) -> Browser:
        raise NotImplementedError

    async def get_cdp_url(self) -> str | None:
        raise NotImplementedError

    @property
    def is_alive(self) -> bool:
        raise NotImplementedError

    @property
    def active(self) -> int:
        return self.max_concurrent - self._semaphore._value

    @property
    def available(self) -> int:
        return self._semaphore._value

    async def browser_page_count(self) -> int:
        """Query actual open page count from the browser via CDP."""
        return -1

    @asynccontextmanager
    async def get_page(
        self,
        *,
        viewport_width: int | None = None,
        viewport_height: int | None = None,
        device_scale_factor: float | None = None,
        color_scheme: str | None = None,
        route_handler: Callable | None = None,
    ) -> AsyncIterator[tuple[BrowserContext, Page]]:
        async with self._semaphore:
            browser = await self.ensure_ready()
            context: BrowserContext | None = None
            try:
                context_kwargs: dict[str, Any] = {
                    "viewport": {
                        "width": viewport_width or settings.viewport_width,
                        "height": viewport_height or settings.viewport_height,
                    },
                    "user_agent": None,
                }
                if device_scale_factor is not None:
                    context_kwargs["device_scale_factor"] = device_scale_factor
                if color_scheme is not None:
                    context_kwargs["color_scheme"] = color_scheme
                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()
                if route_handler:
                    await page.route("**/*", route_handler)
                yield context, page
            finally:
                if context:
                    await context.close()


# ---------------------------------------------------------------------------
# Local worker — spawns a Chromium process on this machine
# ---------------------------------------------------------------------------


class LocalWorker(_BaseWorker):
    """Browser worker backed by a local Chromium process."""

    def __init__(self, cdp_port: int, max_concurrent: int) -> None:
        super().__init__(max_concurrent)
        self.cdp_port = cdp_port
        self.endpoint = "local"
        self.worker_type = "cdp"
        self._playwright = None
        self._browser: Browser | None = None
        self._chrome_proc: subprocess.Popen | None = None  # type: ignore[type-arg]
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        executable_path = _find_browser_binary()
        stealth_args = _get_stealth_args()

        chrome_args = [
            executable_path,
            "--headless",
            f"--remote-debugging-port={self.cdp_port}",
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

        cdp_url = f"http://127.0.0.1:{self.cdp_port}"
        for _ in range(30):
            try:
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

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url)
        self.healthy = True
        logger.info(
            "Local browser started (CloakBrowser %s, CDP on :%d)",
            executable_path,
            self.cdp_port,
        )

    async def stop(self) -> None:
        self.healthy = False
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

    async def ensure_ready(self) -> Browser:
        async with self._lock:
            chrome_dead = (
                self._chrome_proc is None or self._chrome_proc.poll() is not None
            )
            browser_dead = self._browser is None or not self._browser.is_connected()
            if chrome_dead or browser_dead:
                logger.warning("Local browser not connected, restarting...")
                await self.stop()
                await self.start()
            assert self._browser is not None
            return self._browser

    async def get_cdp_url(self) -> str | None:
        await self.ensure_ready()
        try:
            data = await asyncio.to_thread(
                _fetch_json,
                f"http://127.0.0.1:{self.cdp_port}/json/version",
            )
            ws_url = data.get("webSocketDebuggerUrl")
            if ws_url:
                return ws_url
        except Exception:
            logger.debug("Failed to get CDP WebSocket URL", exc_info=True)
        return f"ws://127.0.0.1:{self.cdp_port}"

    async def browser_page_count(self) -> int:
        return await asyncio.to_thread(
            _count_cdp_pages, f"http://127.0.0.1:{self.cdp_port}"
        )

    @property
    def is_alive(self) -> bool:
        return self._browser is not None and self._browser.is_connected()


# ---------------------------------------------------------------------------
# Remote worker — connects to an external CDP endpoint
# ---------------------------------------------------------------------------


class RemoteWorker(_BaseWorker):
    """Browser worker backed by a remote CDP endpoint."""

    def __init__(self, endpoint: str, max_concurrent: int) -> None:
        super().__init__(max_concurrent)
        self.endpoint = endpoint
        self.worker_type = "cdp"
        self._playwright = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        resolved = _resolve_to_ip(self.endpoint)
        self._browser = await self._playwright.chromium.connect_over_cdp(resolved)
        ctx = await self._browser.new_context()
        page = await ctx.new_page()
        await page.close()
        await ctx.close()
        self.healthy = True
        logger.info("Connected to remote browser at %s (verified)", self.endpoint)

    async def stop(self) -> None:
        self.healthy = False
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def ensure_ready(self) -> Browser:
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                logger.warning(
                    "Remote browser %s disconnected, reconnecting...", self.endpoint
                )
                await self.stop()
                await self.start()
            assert self._browser is not None
            return self._browser

    def _http_base(self) -> str:
        return _ws_to_http(_resolve_to_ip(self.endpoint))

    async def get_cdp_url(self) -> str | None:
        await self.ensure_ready()
        try:
            data = await asyncio.to_thread(
                _fetch_json, f"{self._http_base()}/json/version"
            )
            ws_url = data.get("webSocketDebuggerUrl")
            if ws_url:
                return ws_url
        except Exception:
            logger.debug("Failed to get CDP URL for %s", self.endpoint, exc_info=True)
        if self.endpoint.startswith(("ws://", "wss://")):
            return self.endpoint
        return None

    async def browser_page_count(self) -> int:
        return await asyncio.to_thread(_count_cdp_pages, self._http_base())

    @property
    def is_alive(self) -> bool:
        return self._browser is not None and self._browser.is_connected()


# ---------------------------------------------------------------------------
# Playwright-protocol worker — for Firefox/Camoufox
# ---------------------------------------------------------------------------


class PlaywrightWorker(_BaseWorker):
    """Browser worker connected via Playwright protocol (Firefox/Camoufox)."""

    def __init__(self, endpoint: str, max_concurrent: int) -> None:
        super().__init__(max_concurrent)
        self.endpoint = endpoint
        self.worker_type = "playwright"
        self._playwright = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.firefox.connect(self.endpoint)
        ctx = await self._browser.new_context()
        page = await ctx.new_page()
        await page.close()
        await ctx.close()
        self.healthy = True
        logger.info(
            "Connected to Playwright/Firefox browser at %s (verified)", self.endpoint
        )

    async def stop(self) -> None:
        self.healthy = False
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def ensure_ready(self) -> Browser:
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                logger.warning(
                    "Playwright browser %s disconnected, reconnecting...",
                    self.endpoint,
                )
                await self.stop()
                await self.start()
            assert self._browser is not None
            return self._browser

    async def get_cdp_url(self) -> str | None:
        return None

    async def browser_page_count(self) -> int:
        if self._browser and self._browser.is_connected():
            return sum(len(c.pages) for c in self._browser.contexts)
        return -1

    @property
    def is_alive(self) -> bool:
        return self._browser is not None and self._browser.is_connected()


# ---------------------------------------------------------------------------
# BrowserManager — pool coordinator
# ---------------------------------------------------------------------------


class BrowserManager:
    """Manages browser workers — local or remote pool.

    When ``VEILRENDER_WORKERS`` is not set, spawns a single local
    Chromium process (identical to pre-pool behavior). When set,
    connects to remote workers via CDP or Playwright protocol.
    """

    def __init__(self) -> None:
        if settings.workers:
            self._workers: list[_BaseWorker] = []
            for protocol, endpoint in settings.workers:
                if protocol == "playwright":
                    self._workers.append(
                        PlaywrightWorker(endpoint, settings.worker_max_concurrent)
                    )
                else:
                    self._workers.append(
                        RemoteWorker(endpoint, settings.worker_max_concurrent)
                    )
            self._is_local = False
        else:
            self._workers = [LocalWorker(CDP_PORT, settings.max_concurrent)]
            self._is_local = True

        self._health_task: asyncio.Task | None = None  # type: ignore[type-arg]

        if settings.resource_filter:
            self._blocklist = load_blocklist(settings.blocked_domains_extra)
            self._route_handler = make_route_handler(self._blocklist)
        else:
            self._blocklist = frozenset()
            self._route_handler = None

    async def start(self) -> None:
        for w in self._workers:
            try:
                await w.start()
            except Exception:
                logger.error("Failed to start worker %s", w.endpoint, exc_info=True)
                w.healthy = False
        healthy_count = sum(1 for w in self._workers if w.healthy)
        if healthy_count == 0:
            logger.warning("0 of %d workers healthy at startup", len(self._workers))
        if not self._is_local:
            self._health_task = asyncio.create_task(self._health_loop())

    async def stop(self) -> None:
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None
        for w in self._workers:
            await w.stop()
        logger.info("Browser stopped")

    async def _health_loop(self) -> None:
        interval = settings.worker_health_interval
        while True:
            await asyncio.sleep(interval)
            for w in self._workers:
                try:
                    alive = w.is_alive
                    if not alive and w.healthy:
                        logger.warning("Worker %s went unhealthy", w.endpoint)
                        w.healthy = False
                    elif not alive and not w.healthy:
                        logger.info("Attempting reconnect to %s", w.endpoint)
                        try:
                            await w.ensure_ready()
                        except Exception:
                            logger.debug("Reconnect failed for %s", w.endpoint)
                    elif alive and not w.healthy:
                        w.healthy = True
                        logger.info("Worker %s recovered", w.endpoint)
                except Exception:
                    logger.debug("Health check error for %s", w.endpoint, exc_info=True)

    def _pick_worker(self) -> _BaseWorker:
        healthy = [w for w in self._workers if w.healthy]
        if not healthy:
            raise RuntimeError("No healthy browser workers available")
        return max(healthy, key=lambda w: w.available)

    @property
    def active_pages(self) -> int:
        return sum(w.active for w in self._workers)

    @property
    def is_browser_alive(self) -> bool:
        return any(w.is_alive for w in self._workers)

    @property
    def total_capacity(self) -> int:
        return sum(w.max_concurrent for w in self._workers if w.healthy)

    async def worker_stats(self) -> list[dict]:
        result = []
        for i, w in enumerate(self._workers):
            browser_pages = await w.browser_page_count() if w.healthy else -1
            result.append(
                {
                    "index": i,
                    "type": w.worker_type,
                    "endpoint": w.endpoint,
                    "healthy": w.healthy,
                    "active": w.active,
                    "browser_pages": browser_pages,
                    "max_concurrent": w.max_concurrent,
                    "is_alive": w.is_alive,
                }
            )
        return result

    async def get_cdp_url(self, worker_index: int | None = None) -> str | None:
        if worker_index is not None and 0 <= worker_index < len(self._workers):
            w = self._workers[worker_index]
            if w.healthy and w.worker_type == "cdp":
                return await w.get_cdp_url()
            return None
        cdp_workers = [w for w in self._workers if w.healthy and w.worker_type == "cdp"]
        if not cdp_workers:
            return None
        w = max(cdp_workers, key=lambda w: w.available)
        return await w.get_cdp_url()

    @asynccontextmanager
    async def get_page(
        self,
        *,
        viewport_width: int | None = None,
        viewport_height: int | None = None,
        device_scale_factor: float | None = None,
        color_scheme: str | None = None,
    ) -> AsyncIterator[tuple[BrowserContext, Page]]:
        worker = self._pick_worker()
        async with worker.get_page(
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            device_scale_factor=device_scale_factor,
            color_scheme=color_scheme,
            route_handler=self._route_handler,
        ) as result:
            yield result


browser_manager = BrowserManager()
