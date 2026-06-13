"""Dashboard endpoint — GET / stats page."""

from __future__ import annotations

from veilrender import stats
from veilrender._vendor.httpserver import App, Request, Response
from veilrender.browser import browser_manager
from veilrender.config import settings

_BADGES_HTML = """
    <a href="https://github.com/Oaklight/veilrender" target="_blank" rel="noopener">
      <img src="https://img.shields.io/github/stars/Oaklight/veilrender?style=flat&amp;logo=github&amp;label=GitHub" alt="GitHub">
    </a>
    <a href="https://pypi.org/project/veilrender/" target="_blank" rel="noopener">
      <img src="https://img.shields.io/pypi/v/veilrender?style=flat&amp;logo=pypi&amp;logoColor=white&amp;label=PyPI" alt="PyPI">
    </a>
    <a href="https://hub.docker.com/r/oaklight/veilrender" target="_blank" rel="noopener">
      <img src="https://img.shields.io/docker/pulls/oaklight/veilrender?style=flat&amp;logo=docker&amp;logoColor=white&amp;label=Docker" alt="Docker Hub">
    </a>
    <a href="https://huggingface.co/spaces/oaklight/veilrender-public" target="_blank" rel="noopener">
      <img src="https://img.shields.io/badge/%F0%9F%A4%97_HF_Spaces-demo-yellow?style=flat" alt="HF Spaces">
    </a>
"""


def _stats_row(name: str, ep: stats.EndpointStats) -> str:
    """Build an HTML table row for one endpoint."""
    rate_class = "green" if ep.success_rate >= 95 else "yellow" if ep.success_rate >= 80 else "red"
    return f"""
        <tr>
          <td><code>{name}</code></td>
          <td class="mono">{ep.requests}</td>
          <td class="mono green">{ep.successes}</td>
          <td class="mono red">{ep.failures}</td>
          <td class="mono {rate_class}">{ep.success_rate:.1f}%</td>
          <td class="mono">{ep.avg_ms:.0f} ms</td>
          <td class="mono">{ep.p95_ms:.0f} ms</td>
        </tr>"""


def _build_html() -> str:
    """Build the dashboard HTML."""
    browser_status = "🟢 alive" if browser_manager.is_browser_alive else "🔴 dead"
    active = browser_manager.active_pages
    max_conc = settings.max_concurrent

    total_req = stats.render.requests + stats.screenshot.requests
    total_ok = stats.render.successes + stats.screenshot.successes
    total_fail = stats.render.failures + stats.screenshot.failures

    utilization = (active / max_conc * 100) if max_conc > 0 else 0
    util_class = "green" if utilization < 70 else "yellow" if utilization < 90 else "red"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="5">
  <title>VeilRender Dashboard</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f172a; color: #e2e8f0; padding: 2rem;
      min-height: 100vh;
    }}

    /* Header */
    .header {{
      display: flex; align-items: center; justify-content: space-between;
      flex-wrap: wrap; gap: 1rem; margin-bottom: 2rem;
      padding-bottom: 1.5rem; border-bottom: 1px solid #1e293b;
    }}
    .header h1 {{
      font-size: 1.5rem; font-weight: 700; color: #f8fafc;
      letter-spacing: -0.02em;
    }}
    .header h1 span {{ color: #818cf8; }}
    .badges {{ display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }}
    .badges a {{ text-decoration: none; transition: opacity 0.15s; }}
    .badges a:hover {{ opacity: 0.8; }}
    .badges img {{ height: 20px; vertical-align: middle; }}

    /* Section labels */
    .section-label {{
      font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.08em; color: #64748b; margin-bottom: 0.75rem;
    }}

    /* Cards */
    .grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 0.75rem; margin-bottom: 2rem;
    }}
    .card {{
      background: #1e293b; border-radius: 10px; padding: 1.2rem;
      border: 1px solid #334155; transition: border-color 0.2s;
    }}
    .card:hover {{ border-color: #475569; }}
    .card .label {{
      font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
      color: #94a3b8; margin-bottom: 0.4rem;
    }}
    .card .value {{ font-size: 1.6rem; font-weight: 700; font-variant-numeric: tabular-nums; }}

    /* Table */
    .table-wrap {{
      background: #1e293b; border-radius: 10px; border: 1px solid #334155;
      overflow: hidden; margin-bottom: 2rem;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{
      padding: 0.7rem 1rem; text-align: left; font-size: 0.7rem;
      text-transform: uppercase; letter-spacing: 0.06em; color: #94a3b8;
      background: #1e293b; border-bottom: 1px solid #334155;
    }}
    td {{
      padding: 0.7rem 1rem; border-top: 1px solid rgba(51, 65, 85, 0.5);
    }}
    tr:hover td {{ background: rgba(51, 65, 85, 0.3); }}
    code {{ font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace; font-size: 0.9em; }}
    .mono {{ font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace; font-variant-numeric: tabular-nums; }}

    /* Colors */
    .green {{ color: #4ade80; }}
    .yellow {{ color: #facc15; }}
    .red {{ color: #f87171; }}
    .blue {{ color: #60a5fa; }}
    .indigo {{ color: #818cf8; }}

    /* Capacity bar */
    .bar-track {{
      height: 6px; background: #334155; border-radius: 3px;
      margin-top: 0.5rem; overflow: hidden;
    }}
    .bar-fill {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}

    /* Footer */
    .footer {{
      font-size: 0.7rem; color: #475569; display: flex;
      justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;
    }}

    @media (max-width: 640px) {{
      body {{ padding: 1rem; }}
      .header {{ flex-direction: column; align-items: flex-start; }}
      .grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>👻 <span>Veil</span>Render</h1>
    <div class="badges">
      {_BADGES_HTML}
    </div>
  </div>

  <div class="section-label">Overview</div>
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
      <div class="label">Capacity</div>
      <div class="value {util_class}">{active} <span style="font-size:0.8rem;color:#94a3b8">/ {max_conc}</span></div>
      <div class="bar-track">
        <div class="bar-fill" style="width:{utilization:.0f}%;background:{'#4ade80' if utilization < 70 else '#facc15' if utilization < 90 else '#f87171'}"></div>
      </div>
    </div>
    <div class="card">
      <div class="label">Total Requests</div>
      <div class="value indigo">{total_req}</div>
    </div>
    <div class="card">
      <div class="label">Successes</div>
      <div class="value green">{total_ok}</div>
    </div>
    <div class="card">
      <div class="label">Failures</div>
      <div class="value {'red' if total_fail > 0 else 'green'}">{total_fail}</div>
    </div>
  </div>

  <div class="section-label">Endpoints</div>
  <div class="table-wrap">
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
  </div>

  <div class="footer">
    <span>Auto-refreshes every 5s &middot; Stats are in-memory, reset on restart</span>
    <span>VeilRender &middot; Headless browser rendering API</span>
  </div>
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
