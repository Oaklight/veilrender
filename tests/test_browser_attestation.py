"""Tests for worker attestation through the egress proxy canaries.

The fail-closed guarantee rests on ``BrowserManager._verify_worker``: a worker
is only selected when a canary navigation demonstrably arrived through the
proxy. These tests drive that decision with a stub browser whose navigations
either reach the proxy's real socket or never leave the fake.
"""

from __future__ import annotations

import asyncio
import base64
from urllib.parse import urlsplit

from veilrender import browser as browser_module
from veilrender.browser import BrowserManager, LocalWorker, _BaseWorker
from veilrender.egress_proxy import EgressProxy


class _FakePage:
    def __init__(self, deliver, context_kwargs: dict) -> None:
        self._deliver = deliver
        self._context_kwargs = context_kwargs

    async def goto(self, url, **_kwargs) -> None:
        await self._deliver(url, self._context_kwargs)


class _FakeContext:
    def __init__(self, deliver, context_kwargs: dict) -> None:
        self._deliver = deliver
        self._context_kwargs = context_kwargs

    async def new_page(self) -> _FakePage:
        return _FakePage(self._deliver, self._context_kwargs)

    async def close(self) -> None:
        pass


class _FakeBrowser:
    """Browser stand-in; ``deliver(url, context_kwargs)`` models navigation."""

    def __init__(self, deliver) -> None:
        self._deliver = deliver
        self.context_kwargs: list[dict] = []

    async def new_context(self, **kwargs) -> _FakeContext:
        self.context_kwargs.append(kwargs)
        return _FakeContext(self._deliver, kwargs)


class _StubWorker(_BaseWorker):
    """Worker that never launches a browser process."""

    endpoint = "stub"
    worker_type = "stub"

    def __init__(self, browser: _FakeBrowser) -> None:
        super().__init__(1)
        self._browser = browser
        self._alive = True
        self.starts = 0

    async def start(self) -> None:
        self.starts += 1
        self._mark_started()

    async def stop(self) -> None:
        pass

    async def ensure_ready(self):
        await self.start()
        return self._browser

    async def get_cdp_url(self):
        return None

    @property
    def is_alive(self) -> bool:
        return self._alive


class _StubLocalWorker(LocalWorker):
    """Local worker whose browser is a fake (no Chromium launch)."""

    def __init__(self, browser: _FakeBrowser) -> None:
        super().__init__(0, 1)
        self._browser = browser
        self.starts = 0

    async def start(self) -> None:
        self.starts += 1
        self._mark_started()

    async def stop(self) -> None:
        pass

    async def ensure_ready(self):
        await self.start()
        return self._browser


async def _deliver(proxy: EgressProxy, url: str, _context_kwargs: dict) -> None:
    """Send a canary navigation to the proxy the way a browser would."""
    parsed = urlsplit(url)
    if parsed.scheme == "https":
        request_line = f"CONNECT {parsed.hostname}:443 HTTP/1.1"
        host_line = f"Host: {parsed.hostname}:443"
    else:
        request_line = f"GET {url} HTTP/1.1"
        host_line = f"Host: {parsed.netloc}"
    lines = [request_line, host_line]
    if proxy.token:
        encoded = base64.b64encode(f"veilrender:{proxy.token}".encode()).decode()
        lines.append(f"Proxy-Authorization: Basic {encoded}")
    reader, writer = await asyncio.open_connection("127.0.0.1", proxy.port)
    try:
        writer.write(("\r\n".join(lines) + "\r\n\r\n").encode())
        await writer.drain()
        await asyncio.wait_for(reader.read(), timeout=2)
    finally:
        writer.close()


def _manager(proxy: EgressProxy) -> BrowserManager:
    manager = BrowserManager()
    manager._egress_proxy = proxy
    return manager


class _ObservedManager(BrowserManager):
    """Manager that signals when a worker verification has completed."""

    def __init__(self) -> None:
        super().__init__()
        self.verified = asyncio.Event()

    async def _verify_worker(self, worker: _BaseWorker) -> bool:
        try:
            return await super()._verify_worker(worker)
        finally:
            self.verified.set()


def _fast_canary(monkeypatch) -> None:
    """Shorten the canary wait so negative cases fail quickly."""
    original = EgressProxy.wait_canary

    async def fast(self, token, timeout=2.0):
        return await original(self, token, timeout=0.2)

    monkeypatch.setattr(EgressProxy, "wait_canary", fast)


def test_worker_healthy_when_canaries_reach_proxy() -> None:
    async def scenario() -> bool:
        proxy = EgressProxy()
        await proxy.start()
        try:
            browser = _FakeBrowser(lambda url, kwargs: _deliver(proxy, url, kwargs))
            return await _manager(proxy)._verify_worker(_StubWorker(browser))
        finally:
            await proxy.stop()

    assert asyncio.run(scenario()) is True


def test_worker_unhealthy_when_navigation_bypasses_proxy(monkeypatch) -> None:
    _fast_canary(monkeypatch)

    async def scenario() -> bool:
        proxy = EgressProxy()
        await proxy.start()
        try:
            browser = _FakeBrowser(lambda url, kwargs: asyncio.sleep(0))
            return await _manager(proxy)._verify_worker(_StubWorker(browser))
        finally:
            await proxy.stop()

    assert asyncio.run(scenario()) is False


def test_worker_healthy_when_proxy_requires_auth() -> None:
    async def scenario() -> bool:
        proxy = EgressProxy(token="s3cret-token")
        await proxy.start()
        try:
            browser = _FakeBrowser(lambda url, kwargs: _deliver(proxy, url, kwargs))
            return await _manager(proxy)._verify_worker(_StubWorker(browser))
        finally:
            await proxy.stop()

    assert asyncio.run(scenario()) is True


def test_unauthenticated_canary_does_not_attest(monkeypatch) -> None:
    _fast_canary(monkeypatch)

    async def scenario() -> bool:
        proxy = EgressProxy(token="s3cret-token")
        await proxy.start()
        try:
            browser = _FakeBrowser(lambda url, kwargs: asyncio.sleep(0))
            return await _manager(proxy)._verify_worker(_StubWorker(browser))
        finally:
            await proxy.stop()

    assert asyncio.run(scenario()) is False


def test_local_worker_checks_browser_level_proxy_path(monkeypatch) -> None:
    """A browser that honours only the context proxy fails the /cdp path check."""
    _fast_canary(monkeypatch)

    async def scenario(honour_browser_level: bool) -> bool:
        proxy = EgressProxy()
        await proxy.start()
        try:

            def deliver(url, kwargs):
                if "proxy" in kwargs or honour_browser_level:
                    return _deliver(proxy, url, kwargs)
                return asyncio.sleep(0)

            browser = _FakeBrowser(deliver)
            return await _manager(proxy)._verify_worker(_StubLocalWorker(browser))
        finally:
            await proxy.stop()

    assert asyncio.run(scenario(honour_browser_level=True)) is True
    assert asyncio.run(scenario(honour_browser_level=False)) is False


def test_reconnect_is_reattested_by_the_health_loop(monkeypatch) -> None:
    """A reconnect that loses the proxy path leaves the worker unhealthy."""
    _fast_canary(monkeypatch)
    monkeypatch.setattr(browser_module.settings, "worker_health_interval", 0.01)

    async def scenario(bypass: bool) -> bool:
        proxy = EgressProxy()
        await proxy.start()
        worker = _StubWorker(
            _FakeBrowser(
                (lambda url, kwargs: asyncio.sleep(0))
                if bypass
                else (lambda url, kwargs: _deliver(proxy, url, kwargs))
            )
        )
        worker.healthy = True
        worker._alive = False
        manager = _ObservedManager()
        manager._egress_proxy = proxy
        manager._workers = [worker]

        task = asyncio.create_task(manager._health_loop())
        try:
            await asyncio.wait_for(manager.verified.wait(), timeout=3)
            assert worker.starts > 0, "health loop never reconnected"
            return worker.healthy
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await proxy.stop()

    assert asyncio.run(scenario(bypass=False)) is True
    assert asyncio.run(scenario(bypass=True)) is False


def test_mark_started_only_restores_health_without_enforcement(monkeypatch) -> None:
    worker = _StubWorker(_FakeBrowser(lambda url, kwargs: asyncio.sleep(0)))

    monkeypatch.setattr(browser_module.settings, "egress_proxy", True)
    worker.healthy = False
    worker._mark_started()
    assert worker.healthy is False

    monkeypatch.setattr(browser_module.settings, "egress_proxy", False)
    worker._mark_started()
    assert worker.healthy is True
