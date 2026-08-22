"""Prometheus metrics endpoint — GET /metrics."""

from __future__ import annotations

from veilrender import stats
from veilrender._vendor.httpserver import App, Request, Response
from veilrender.browser import browser_manager
from veilrender.config import settings

_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"
_ENDPOINTS = (("/render", stats.render), ("/screenshot", stats.screenshot))


def _build_metrics() -> str:
    """Build Prometheus exposition text."""
    active = browser_manager.active_pages
    alive = 1 if browser_manager.is_browser_alive else 0
    parts: list[str] = []

    # Gauges
    parts.append(
        "# HELP veilrender_uptime_seconds Process uptime in seconds.\n"
        "# TYPE veilrender_uptime_seconds gauge\n"
        f"veilrender_uptime_seconds {stats.uptime_seconds():.1f}\n"
    )
    parts.append(
        "# HELP veilrender_browser_alive Whether the browser process is alive.\n"
        "# TYPE veilrender_browser_alive gauge\n"
        f"veilrender_browser_alive {alive}\n"
    )
    parts.append(
        "# HELP veilrender_active_pages Current number of active browser pages.\n"
        "# TYPE veilrender_active_pages gauge\n"
        f"veilrender_active_pages {active}\n"
    )
    parts.append(
        "# HELP veilrender_max_concurrent Maximum concurrent page slots.\n"
        "# TYPE veilrender_max_concurrent gauge\n"
        f"veilrender_max_concurrent {settings.max_concurrent}\n"
    )

    # Counters — requests
    lines = [
        "# HELP veilrender_requests_total Total requests by endpoint and status.\n",
        "# TYPE veilrender_requests_total counter\n",
    ]
    for name, ep in _ENDPOINTS:
        lines.append(
            f'veilrender_requests_total{{endpoint="{name}",status="success"}} {ep.successes}\n'
        )
        lines.append(
            f'veilrender_requests_total{{endpoint="{name}",status="failure"}} {ep.failures}\n'
        )
    parts.append("".join(lines))

    # Counters — cache
    lines = [
        "# HELP veilrender_cache_lookups_total Cache lookups by endpoint and result.\n",
        "# TYPE veilrender_cache_lookups_total counter\n",
    ]
    for name, ep in _ENDPOINTS:
        lines.append(
            f'veilrender_cache_lookups_total{{endpoint="{name}",result="hit"}} {ep.cache_hits}\n'
        )
        lines.append(
            f'veilrender_cache_lookups_total{{endpoint="{name}",result="miss"}} {ep.cache_misses}\n'
        )
    parts.append("".join(lines))

    # Latency — summary with quantiles, _sum, _count
    lines = [
        "# HELP veilrender_request_duration_seconds Request latency in seconds.\n",
        "# TYPE veilrender_request_duration_seconds summary\n",
    ]
    for name, ep in _ENDPOINTS:
        count = ep.successes + ep.failures
        lines.append(
            f'veilrender_request_duration_seconds{{endpoint="{name}",quantile="0.5"}} {ep.p50_ms / 1000:.6f}\n'
        )
        lines.append(
            f'veilrender_request_duration_seconds{{endpoint="{name}",quantile="0.95"}} {ep.p95_ms / 1000:.6f}\n'
        )
        lines.append(
            f'veilrender_request_duration_seconds_sum{{endpoint="{name}"}} {ep.total_ms / 1000:.6f}\n'
        )
        lines.append(
            f'veilrender_request_duration_seconds_count{{endpoint="{name}"}} {count}\n'
        )
    parts.append("".join(lines))

    return "\n".join(parts)


def register(app: App) -> None:
    """Register metrics route on the app."""

    @app.get("/metrics")
    async def metrics(request: Request) -> Response:
        return Response(
            body=_build_metrics(),
            status_code=200,
            content_type=_CONTENT_TYPE,
            headers={"Cache-Control": "no-store"},
        )
