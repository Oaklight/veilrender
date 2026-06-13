"""Dashboard endpoint — GET / stats page."""

from __future__ import annotations

from veilrender import stats
from veilrender._vendor.httpserver import App, Request, Response
from veilrender.browser import browser_manager
from veilrender.config import settings


def _stats_row(name: str, ep: stats.EndpointStats) -> str:
    """Build an HTML table row for one endpoint."""
    return f"""
        <tr>
          <td>{name}</td>
          <td>{ep.requests}</td>
          <td>{ep.successes}</td>
          <td>{ep.failures}</td>
          <td>{ep.success_rate:.1f}%</td>
          <td>{ep.avg_ms:.0f} ms</td>
          <td>{ep.p95_ms:.0f} ms</td>
        </tr>"""


def _build_html() -> str:
    """Build the dashboard HTML."""
    browser_status = "🟢 alive" if browser_manager.is_browser_alive else "🔴 dead"
    active = browser_manager.active_pages
    max_conc = settings.max_concurrent

    total_req = stats.render.requests + stats.screenshot.requests
    total_ok = stats.render.successes + stats.screenshot.successes
    total_fail = stats.render.failures + stats.screenshot.failures

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="5">
  <title>VeilRender Dashboard</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #0f172a; color: #e2e8f0; padding: 2rem; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 1.5rem; color: #f8fafc; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
             gap: 1rem; margin-bottom: 2rem; }}
    .card {{ background: #1e293b; border-radius: 8px; padding: 1.2rem; }}
    .card .label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
                    color: #94a3b8; margin-bottom: 0.3rem; }}
    .card .value {{ font-size: 1.5rem; font-weight: 600; }}
    .green {{ color: #4ade80; }}
    .red {{ color: #f87171; }}
    .blue {{ color: #60a5fa; }}
    table {{ width: 100%; border-collapse: collapse; background: #1e293b;
             border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 0.75rem 1rem; text-align: left; }}
    th {{ background: #334155; font-size: 0.75rem; text-transform: uppercase;
         letter-spacing: 0.05em; color: #94a3b8; }}
    td {{ border-top: 1px solid #334155; }}
    .footer {{ margin-top: 2rem; font-size: 0.75rem; color: #64748b; }}
  </style>
</head>
<body>
  <h1>👻 VeilRender Dashboard</h1>

  <div class="grid">
    <div class="card">
      <div class="label">Uptime</div>
      <div class="value">{stats.format_uptime()}</div>
    </div>
    <div class="card">
      <div class="label">Browser</div>
      <div class="value">{browser_status}</div>
    </div>
    <div class="card">
      <div class="label">Active Pages</div>
      <div class="value blue">{active} / {max_conc}</div>
    </div>
    <div class="card">
      <div class="label">Total Requests</div>
      <div class="value">{total_req}</div>
    </div>
    <div class="card">
      <div class="label">Successes</div>
      <div class="value green">{total_ok}</div>
    </div>
    <div class="card">
      <div class="label">Failures</div>
      <div class="value red">{total_fail}</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Endpoint</th>
        <th>Requests</th>
        <th>Success</th>
        <th>Failure</th>
        <th>Rate</th>
        <th>Avg Latency</th>
        <th>P95 Latency</th>
      </tr>
    </thead>
    <tbody>
      {_stats_row("/render", stats.render)}
      {_stats_row("/screenshot", stats.screenshot)}
    </tbody>
  </table>

  <div class="footer">Auto-refreshes every 5 seconds &middot; Stats are in-memory and reset on restart</div>
</body>
</html>"""


def register(app: App) -> None:
    """Register dashboard route on the app."""

    @app.get("/")
    async def dashboard(request: Request) -> Response:
        return Response(
            body=_build_html(),
            status_code=200,
            content_type="text/html; charset=utf-8",
        )
