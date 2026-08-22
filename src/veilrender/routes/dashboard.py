"""Dashboard endpoint — GET / stats page + GET /stats JSON API."""

from __future__ import annotations

import json

from veilrender import stats
from veilrender._vendor.httpserver import App, Request, Response
from veilrender.browser import browser_manager
from veilrender.config import settings

_BADGE_STYLE = "style=flat&amp;labelColor=1a1d1d&amp;color=2d3d32"

_BADGES_HTML = f"""
    <a href="https://github.com/Oaklight/veilrender" target="_blank" rel="noopener">
      <img src="https://img.shields.io/github/stars/Oaklight/veilrender?{_BADGE_STYLE}&amp;logo=github&amp;logoColor=6abf7b&amp;label=GitHub" alt="GitHub">
    </a>
    <a href="https://pypi.org/project/veilrender/" target="_blank" rel="noopener">
      <img src="https://img.shields.io/pypi/v/veilrender?{_BADGE_STYLE}&amp;logo=pypi&amp;logoColor=6abf7b&amp;label=PyPI" alt="PyPI">
    </a>
    <a href="https://hub.docker.com/r/oaklight/veilrender" target="_blank" rel="noopener">
      <img src="https://img.shields.io/docker/pulls/oaklight/veilrender?{_BADGE_STYLE}&amp;logo=docker&amp;logoColor=6abf7b&amp;label=Docker" alt="Docker Hub">
    </a>

"""


def _stats_json() -> dict:
    """Collect all dashboard data as a dict."""
    active = browser_manager.active_pages
    max_conc = settings.max_concurrent
    return {
        "browser_alive": browser_manager.is_browser_alive,
        "uptime": stats.format_uptime(),
        "active": active,
        "max_concurrent": max_conc,
        "utilization": (active / max_conc * 100) if max_conc > 0 else 0,
        "total_requests": stats.render.requests + stats.screenshot.requests,
        "total_successes": stats.render.successes + stats.screenshot.successes,
        "total_failures": stats.render.failures + stats.screenshot.failures,
        "endpoints": {
            "/render": _ep_dict(stats.render),
            "/screenshot": _ep_dict(stats.screenshot),
        },
    }


def _ep_dict(ep: stats.EndpointStats) -> dict:
    """Serialize one endpoint's stats."""
    return {
        "requests": ep.requests,
        "successes": ep.successes,
        "failures": ep.failures,
        "success_rate": round(ep.success_rate, 1),
        "avg_ms": round(ep.avg_ms),
        "p95_ms": round(ep.p95_ms),
    }


def _rate_class(rate: float) -> str:
    if rate >= 95:
        return "c-ok"
    return "c-warn" if rate >= 80 else "c-err"


def _stats_row(name: str, ep: stats.EndpointStats) -> str:
    """Build an HTML table row for one endpoint."""
    return f"""
        <tr>
          <td><code>{name}</code></td>
          <td class="mono" data-ep="{name}" data-f="requests">{ep.requests}</td>
          <td class="mono c-ok" data-ep="{name}" data-f="successes">{ep.successes}</td>
          <td class="mono c-err" data-ep="{name}" data-f="failures">{ep.failures}</td>
          <td class="mono {_rate_class(ep.success_rate)}" data-ep="{name}" data-f="rate">{ep.success_rate:.1f}%</td>
          <td class="mono" data-ep="{name}" data-f="avg">{ep.avg_ms:.0f} ms</td>
          <td class="mono" data-ep="{name}" data-f="p95">{ep.p95_ms:.0f} ms</td>
        </tr>"""


def _capacity_ring(active: int, max_conc: int, utilization: float) -> str:
    """Build an SVG ring gauge for capacity."""
    radius = 40
    circumference = 2 * 3.14159 * radius
    filled = circumference * utilization / 100
    gap = circumference - filled
    color = (
        "#6ee7b7" if utilization < 70 else "#fbbf24" if utilization < 90 else "#f87171"
    )
    return f"""
    <svg viewBox="0 0 100 100" class="ring-gauge">
      <circle cx="50" cy="50" r="{radius}" fill="none"
              stroke="rgba(255,255,255,0.05)" stroke-width="6"/>
      <circle cx="50" cy="50" r="{radius}" fill="none" id="ring-fill"
              stroke="{color}" stroke-width="6"
              stroke-dasharray="{filled:.1f} {gap:.1f}"
              stroke-linecap="round"
              transform="rotate(-90 50 50)"
              style="filter:drop-shadow(0 0 6px {color}50);transition:stroke-dasharray .6s,stroke .6s"/>
      <text x="50" y="47" text-anchor="middle" class="ring-num" id="ring-active">{active}</text>
      <text x="50" y="62" text-anchor="middle" class="ring-sub" id="ring-max">/ {max_conc}</text>
    </svg>"""


def _build_html() -> str:
    """Build the dashboard HTML."""
    browser_alive = browser_manager.is_browser_alive
    browser_label = "alive" if browser_alive else "dead"
    dot_cls = "dot-on" if browser_alive else "dot-off"
    active = browser_manager.active_pages
    max_conc = settings.max_concurrent

    total_req = stats.render.requests + stats.screenshot.requests
    total_ok = stats.render.successes + stats.screenshot.successes
    total_fail = stats.render.failures + stats.screenshot.failures

    utilization = (active / max_conc * 100) if max_conc > 0 else 0
    ring_svg = _capacity_ring(active, max_conc, utilization)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>VeilRender Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,700;1,400&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --black: #000000;
      --surface: #111313;
      --border: #222626;
      --border-hi: #333838;
      --mint: #cdffd8;
      --mint-dim: #6abf7b;
      --text: #d8ece0;
      --text-2: #7a9882;
      --text-3: #4a6650;
      --ok: #6ee7b7;
      --warn: #fbbf24;
      --err: #f87171;
      --ff: 'DM Sans', system-ui, sans-serif;
      --fm: 'JetBrains Mono', 'SF Mono', monospace;
    }}

    *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: var(--ff);
      background: var(--black);
      color: var(--text);
      min-height: 100vh;
    }}

    body::before {{
      content: '';
      position: fixed; top: 0; left: 0; right: 0; height: 500px;
      background: radial-gradient(ellipse 80% 60% at 50% -10%, rgba(110,231,183,0.07) 0%, transparent 70%);
      pointer-events: none;
    }}

    .wrap {{
      position: relative;
      max-width: 1080px;
      margin: 0 auto;
      padding: 3rem 2.5rem 2.5rem;
    }}

    /* Header */
    .hdr {{
      display: flex; align-items: center; justify-content: space-between;
      flex-wrap: wrap; gap: 1.25rem;
      margin-bottom: 3rem;
    }}
    .brand {{ display: flex; align-items: center; gap: 0.75rem; }}
    .brand .ghost {{
      font-size: 2.4rem;
      animation: hover 3s ease-in-out infinite;
    }}
    @keyframes hover {{
      0%, 100% {{ transform: translateY(0); }}
      50% {{ transform: translateY(-5px); }}
    }}
    .brand h1 {{
      font-size: 1.75rem; font-weight: 700; letter-spacing: -0.03em;
      color: var(--mint);
    }}
    .brand h1 span {{ color: var(--text); }}

    /* Lang select */
    .lang-sel {{
      font-family: var(--ff); font-size: 0.7rem; font-weight: 500;
      background: var(--surface); color: var(--text-2);
      border: 1px solid var(--border); border-radius: 6px;
      padding: 0.3rem 0.5rem; cursor: pointer;
      transition: border-color 0.2s, color 0.2s;
      -webkit-appearance: none; appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%234a6650'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 0.4rem center;
      padding-right: 1.3rem;
    }}
    .lang-sel:hover {{ border-color: var(--border-hi); color: var(--text); }}
    .lang-sel option {{ background: var(--surface); color: var(--text); }}

    /* Section label */
    .sec {{
      font-size: 0.7rem; font-weight: 500; text-transform: uppercase;
      letter-spacing: 0.12em; color: var(--text-3);
      margin-bottom: 0.9rem;
    }}

    /* Card */
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      transition: border-color 0.2s;
    }}
    .card:hover {{ border-color: var(--border-hi); }}

    /* Status row */
    .status {{ display: flex; gap: 0.75rem; margin-bottom: 2rem; }}
    .status .card {{
      flex: 1; padding: 1.15rem 1.5rem;
      display: flex; align-items: center; gap: 0.85rem;
    }}
    .dot {{ width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; transition: background 0.3s, box-shadow 0.3s; }}
    .dot-on {{
      background: var(--ok);
      box-shadow: 0 0 0 3px rgba(110,231,183,0.15), 0 0 8px rgba(110,231,183,0.35);
      animation: pulse 2.5s ease-in-out infinite;
    }}
    .dot-off {{
      background: var(--err);
      box-shadow: 0 0 0 3px rgba(248,113,113,0.15);
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.45; }}
    }}
    .s-label {{
      font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em;
      color: var(--text-2);
    }}
    .s-val {{
      font-family: var(--fm); font-weight: 500; font-size: 1.05rem;
      transition: color 0.3s;
    }}

    /* Metrics grid */
    .metrics {{
      display: grid;
      grid-template-columns: 160px 1fr;
      gap: 0.75rem;
      margin-bottom: 2rem;
    }}
    .ring-card {{
      padding: 1.4rem;
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem;
    }}
    .ring-lbl {{
      font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
      color: var(--text-2);
    }}
    .ring-gauge {{ width: 120px; height: 120px; }}
    .ring-num {{
      font-family: var(--fm); font-size: 22px; font-weight: 700;
      fill: var(--mint);
    }}
    .ring-sub {{
      font-family: var(--fm); font-size: 11px; fill: var(--text-2);
    }}
    .nums {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }}
    .num {{ padding: 1.3rem 1.4rem; }}
    .num .lbl {{
      font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em;
      color: var(--text-2); margin-bottom: 0.4rem;
    }}
    .num .val {{
      font-family: var(--fm); font-size: 1.8rem; font-weight: 700;
      font-variant-numeric: tabular-nums; line-height: 1;
      transition: color 0.3s;
    }}
    .c-mint {{ color: var(--mint); }}
    .c-ok {{ color: var(--ok); }}
    .c-warn {{ color: var(--warn); }}
    .c-err {{ color: var(--err); }}

    /* Table */
    .tbl {{ margin-bottom: 2.5rem; overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{
      padding: 0.85rem 1.25rem; text-align: left;
      font-size: 0.7rem; font-weight: 500; text-transform: uppercase;
      letter-spacing: 0.07em; color: var(--text-3);
      border-bottom: 1px solid var(--border);
    }}
    td {{
      padding: 0.85rem 1.25rem; font-size: 0.95rem;
      border-top: 1px solid rgba(255,255,255,0.03);
      transition: color 0.3s;
    }}
    tr:hover td {{ background: rgba(255,255,255,0.015); }}
    code {{
      font-family: var(--fm); font-size: 0.88em;
      color: var(--mint-dim); background: rgba(110,231,183,0.08);
      padding: 0.15em 0.5em; border-radius: 4px;
    }}
    .mono {{ font-family: var(--fm); font-variant-numeric: tabular-nums; }}

    /* Footer */
    .ftr {{
      font-size: 0.7rem; color: var(--text-3);
      padding-top: 1.25rem;
      border-top: 1px solid var(--border);
      display: flex; flex-direction: column; gap: 0.75rem;
    }}
    .ftr a {{ color: var(--mint-dim); text-decoration: none; }}
    .ftr a:hover {{ color: var(--mint); }}
    .ftr-row {{
      display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;
    }}
    .ftr-badges {{
      display: flex; gap: 0.4rem; flex-wrap: wrap; align-items: center;
    }}
    .ftr-badges a {{ opacity: 0.6; transition: opacity 0.2s; }}
    .ftr-badges a:hover {{ opacity: 1; }}
    .ftr-badges img {{ height: 18px; vertical-align: middle; }}

    /* Responsive */
    @media (max-width: 720px) {{
      .wrap {{ padding: 2rem 1.25rem; }}
      .hdr {{ flex-direction: column; align-items: flex-start; }}
      .status {{ flex-direction: column; }}
      .metrics {{ grid-template-columns: 1fr; }}
      .ring-card {{ justify-content: flex-start; padding-left: 2rem; }}
      .nums {{ grid-template-columns: repeat(2, 1fr); }}
    }}

    /* Entrance */
    .in {{ animation: up 0.35s ease-out both; }}
    .d1 {{ animation-delay: 0s; }}
    .d2 {{ animation-delay: 0.05s; }}
    .d3 {{ animation-delay: 0.1s; }}
    .d4 {{ animation-delay: 0.15s; }}
    @keyframes up {{
      from {{ opacity: 0; transform: translateY(10px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
  </style>
</head>
<body>
<div class="wrap">

  <div class="hdr in d1">
    <div class="brand">
      <span class="ghost">👻</span>
      <h1>Veil<span>Render</span></h1>
    </div>
    <select class="lang-sel" id="lang-sel" onchange="setLang(this.value)"></select>
  </div>

  <div class="sec in d1" data-i18n="sec_status">Status</div>
  <div class="status in d2">
    <div class="card">
      <span class="dot {dot_cls}" id="dot"></span>
      <span class="s-label" data-i18n="browser">Browser</span>
      <span class="s-val" id="browser-val" data-i18n-key="browser_status">{browser_label}</span>
    </div>
    <div class="card">
      <span class="s-label" data-i18n="uptime">Uptime</span>
      <span class="s-val" id="uptime-val">{stats.format_uptime()}</span>
    </div>
  </div>

  <div class="sec in d2" data-i18n="sec_metrics">Metrics</div>
  <div class="metrics in d3">
    <div class="card ring-card">
      {ring_svg}
      <div class="ring-lbl" data-i18n="capacity">Capacity</div>
    </div>
    <div class="nums">
      <div class="card num">
        <div class="lbl" data-i18n="requests">Requests</div>
        <div class="val c-mint" id="total-req">{total_req}</div>
      </div>
      <div class="card num">
        <div class="lbl" data-i18n="successes">Successes</div>
        <div class="val c-ok" id="total-ok">{total_ok}</div>
      </div>
      <div class="card num">
        <div class="lbl" data-i18n="failures">Failures</div>
        <div class="val {"c-err" if total_fail > 0 else "c-ok"}" id="total-fail">{total_fail}</div>
      </div>
    </div>
  </div>

  <div class="sec in d3" data-i18n="sec_endpoints">Endpoints</div>
  <div class="card tbl in d4">
    <table>
      <thead>
        <tr>
          <th data-i18n="th_endpoint">Endpoint</th>
          <th data-i18n="th_requests">Requests</th>
          <th data-i18n="th_success">Success</th>
          <th data-i18n="th_failure">Failure</th>
          <th data-i18n="th_rate">Rate</th>
          <th data-i18n="th_avg">Avg Latency</th>
          <th data-i18n="th_p95">P95 Latency</th>
        </tr>
      </thead>
      <tbody>
        {_stats_row("/render", stats.render)}
        {_stats_row("/screenshot", stats.screenshot)}
      </tbody>
    </table>
  </div>

  <div class="ftr in d4">
    <div class="ftr-row">
      <span data-i18n="footer_info">Live updates every 5 s · stats are in-memory, reset on restart</span>
      <span data-i18n="footer_author">Built by <a href="https://github.com/Oaklight">Oaklight</a> · <a href="https://github.com/Oaklight/veilrender">source on GitHub</a></span>
    </div>
    <div class="ftr-badges">
      {_BADGES_HTML}
    </div>
  </div>

</div>
<script>
(function() {{
  /* ——— i18n ——— */
  var I18N = {{
    en: {{
      _label: 'English',
      sec_status: 'Status',
      sec_metrics: 'Metrics',
      sec_endpoints: 'Endpoints',
      browser: 'Browser',
      uptime: 'Uptime',
      capacity: 'Capacity',
      requests: 'Requests',
      successes: 'Successes',
      failures: 'Failures',
      th_endpoint: 'Endpoint',
      th_requests: 'Requests',
      th_success: 'Success',
      th_failure: 'Failure',
      th_rate: 'Rate',
      th_avg: 'Avg Latency',
      th_p95: 'P95 Latency',
      footer_info: 'Live updates every 5 s · stats are in-memory, reset on restart',
      footer_author: 'Built by Oaklight · source on GitHub',
      alive: 'alive',
      dead: 'dead'
    }},
    zh: {{
      _label: '中文',
      sec_status: '状态',
      sec_metrics: '指标',
      sec_endpoints: '接口',
      browser: '浏览器',
      uptime: '运行时间',
      capacity: '容量',
      requests: '请求数',
      successes: '成功',
      failures: '失败',
      th_endpoint: '接口',
      th_requests: '请求',
      th_success: '成功',
      th_failure: '失败',
      th_rate: '成功率',
      th_avg: '平均延迟',
      th_p95: 'P95 延迟',
      footer_info: '每 5 秒自动更新 · 统计数据存储在内存中，重启后重置',
      footer_author: '由 Oaklight 构建 · 源码见 GitHub',
      alive: '运行中',
      dead: '已停止'
    }}
  }};

  var lang = localStorage.getItem('vr_lang') || 'en';
  var sel = document.getElementById('lang-sel');

  // Populate select options from I18N keys
  Object.keys(I18N).forEach(function(k) {{
    var opt = document.createElement('option');
    opt.value = k;
    opt.textContent = I18N[k]._label;
    sel.appendChild(opt);
  }});

  function applyLang(l) {{
    lang = l;
    localStorage.setItem('vr_lang', l);
    sel.value = l;
    var t = I18N[l];
    document.querySelectorAll('[data-i18n]').forEach(function(el) {{
      var key = el.getAttribute('data-i18n');
      if (t[key] != null) el.textContent = t[key];
    }});
    var bv = document.getElementById('browser-val');
    if (bv.getAttribute('data-i18n-key') === 'browser_status') {{
      var alive = document.getElementById('dot').classList.contains('dot-on');
      bv.textContent = alive ? t.alive : t.dead;
    }}
    document.documentElement.lang = l;
  }}

  window.setLang = function(l) {{ applyLang(l); }};

  applyLang(lang);

  /* ——— Live data polling ——— */
  var CIRC = 2 * Math.PI * 40;
  function rateClass(r) {{ return r >= 95 ? 'c-ok' : r >= 80 ? 'c-warn' : 'c-err'; }}
  function ringColor(u) {{ return u < 70 ? '#6ee7b7' : u < 90 ? '#fbbf24' : '#f87171'; }}

  function update() {{
    fetch('/stats').then(function(r) {{ return r.json(); }}).then(function(d) {{
      var t = I18N[lang];

      var dot = document.getElementById('dot');
      dot.className = 'dot ' + (d.browser_alive ? 'dot-on' : 'dot-off');
      document.getElementById('browser-val').textContent = d.browser_alive ? t.alive : t.dead;
      document.getElementById('uptime-val').textContent = d.uptime;

      var u = d.utilization;
      var filled = CIRC * u / 100;
      var gap = CIRC - filled;
      var col = ringColor(u);
      var ring = document.getElementById('ring-fill');
      ring.setAttribute('stroke-dasharray', filled.toFixed(1) + ' ' + gap.toFixed(1));
      ring.setAttribute('stroke', col);
      ring.style.filter = 'drop-shadow(0 0 6px ' + col + '50)';
      document.getElementById('ring-active').textContent = d.active;
      document.getElementById('ring-max').textContent = '/ ' + d.max_concurrent;

      document.getElementById('total-req').textContent = d.total_requests;
      document.getElementById('total-ok').textContent = d.total_successes;
      var failEl = document.getElementById('total-fail');
      failEl.textContent = d.total_failures;
      failEl.className = 'val ' + (d.total_failures > 0 ? 'c-err' : 'c-ok');

      var eps = d.endpoints;
      for (var name in eps) {{
        var e = eps[name];
        var cells = document.querySelectorAll('[data-ep="' + name + '"]');
        cells.forEach(function(c) {{
          var f = c.getAttribute('data-f');
          if (f === 'requests') c.textContent = e.requests;
          else if (f === 'successes') c.textContent = e.successes;
          else if (f === 'failures') c.textContent = e.failures;
          else if (f === 'rate') {{
            c.textContent = e.success_rate.toFixed(1) + '%';
            c.className = 'mono ' + rateClass(e.success_rate);
          }}
          else if (f === 'avg') c.textContent = e.avg_ms + ' ms';
          else if (f === 'p95') c.textContent = e.p95_ms + ' ms';
        }});
      }}
    }}).catch(function() {{}});
  }}

  setInterval(update, 5000);
}})();
</script>
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

    @app.get("/stats")
    async def stats_api(request: Request) -> Response:
        return Response(
            body=json.dumps(_stats_json()),
            status_code=200,
            content_type="application/json",
        )
