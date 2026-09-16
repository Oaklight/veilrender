---
name: veilrender
version: 0.6.1
description: "Render JavaScript-heavy pages via VeilRender API: two-tier stealth browser (Obscura + Chromium/Firefox fallback) returns fully rendered HTML, Markdown, readability text, or PNG/JPEG screenshots from URLs that fail with plain HTTP fetch."
homepage: https://github.com/Oaklight/veilrender
metadata:
  {
    "openclaw":
      {
        "emoji": "👻",
        "requires": { "bins": ["curl"] },
      },
  }
---

# VeilRender — Headless Browser Rendering

Render JavaScript-heavy or bot-protected pages via a VeilRender API instance.
Use this when `curl`/`fetch` returns empty or incomplete content because the
page requires a real browser to render.

Two-tier stealth browser: Obscura (Rust, tier 0, ~85ms) with automatic
fallback to Chromium/Firefox (tier 1). `X-Render-Engine` header reports
`alpha` (tier 0) or `beta` (tier 1) when enabled.

## Setup

Config persisted in `~/.config/veilrender/config.json` (`0600`).

Load saved config (or detect env vars), then verify:
```bash
eval $(python3 -c "
import json, os, pathlib
cfg = {}
p = pathlib.Path.home() / '.config' / 'veilrender' / 'config.json'
if p.exists(): cfg = json.loads(p.read_text())
url = os.environ.get('VEILRENDER_URL') or cfg.get('url', '')
token = os.environ.get('VEILRENDER_TOKEN') or cfg.get('token', '')
print(f'export VEILRENDER_URL=\"{url}\"')
print(f'export VEILRENDER_TOKEN=\"{token}\"')
")
curl -sf "$VEILRENDER_URL/health" | jq .
```

If URL is missing, ask the user. Self-hosting option:
```bash
docker run -d -p 7860:7860 -e VEILRENDER_API_TOKEN=changeme -e VEILRENDER_OBSCURA=true oaklight/veilrender:latest
```

Save config:
```bash
python3 -c "
import json, os, pathlib
d = pathlib.Path.home() / '.config' / 'veilrender'; d.mkdir(parents=True, exist_ok=True)
p = d / 'config.json'; p.write_text(json.dumps({'url': '$URL', 'token': '$TOKEN'}, indent=2))
os.chmod(p, 0o600); print(f'Saved to {p}')
"
```

## Render a page

```bash
curl -s -X POST "$VEILRENDER_URL/render" \
  -H "Authorization: Bearer $VEILRENDER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "formats": ["readability"]}' | jq .
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | *(required)* | URL to render |
| `formats` | string[] | `["html"]` | `html`, `readability`, `markdown` |
| `wait_until` | string | `"load"` | `load`, `domcontentloaded`, `networkidle` |
| `timeout` | int | `30000` | Navigation timeout (ms) |

Response: `{"content": {"html": "...", "readability": "...", "markdown": "..."}, "metadata": {"title": "...", "url": "...", "status_code": 200}, "links": [...]}`

## Take a screenshot

```bash
# PNG (default)
curl -s -X POST "$VEILRENDER_URL/screenshot" \
  -H "Authorization: Bearer $VEILRENDER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' -o screenshot.png

# Full-page, JPEG, dark mode, retina — combine options as needed:
# "full_page": true, "format": "jpeg", "quality": 80,
# "color_scheme": "dark", "scale": 2, "selector": "#main",
# "clip": {"x":0,"y":0,"width":400,"height":300}, "transparent": true
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | *(required)* | URL to screenshot |
| `format` | string | `"png"` | `png`, `jpeg` |
| `quality` | int | — | JPEG quality 0–100 |
| `full_page` | bool | `false` | Full scrollable page |
| `scale` | float | — | Device pixel ratio (max `8`) |
| `selector` | string | — | CSS selector for element screenshot |
| `clip` | object | — | `{"x", "y", "width", "height"}` |
| `color_scheme` | string | — | `light`, `dark`, `no-preference` |
| `wait_for` | string | — | CSS selector to wait for |
| `transparent` | bool | `false` | Transparent background (PNG) |
| `timeout` | int | `30000` | Navigation timeout (ms) |
| `viewport_width` | int | `1280` | Viewport width |
| `viewport_height` | int | `720` | Viewport height |

## Error handling

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | — |
| 400 | Bad request (invalid URL, blocked scheme) | Fix request |
| 403 | Auth failed | Check token |
| 429 | Rate limited | Wait `Retry-After` seconds |
| 502 | Browser render failed | Try different URL or longer `timeout` |
| 503 | Server overloaded | Wait `Retry-After` seconds |
| 504 | Request deadline exceeded (45s) | Page too slow |

## Other endpoints

- `GET /health` → `{"status": "ok"}`
- `GET /stats` → JSON dashboard data (tiers, queue depth, latency)
- `GET /metrics` → Prometheus exposition format
- `GET /` → Stats dashboard (no auth)

## Notes

- Two-tier stealth: Obscura (tier 0) for speed, Chromium/Firefox (tier 1) for compatibility — both include anti-detection
- Ad/tracker domains blocked by default (`VEILRENDER_RESOURCE_FILTER=true`)
- Font CSS cached locally — no external network during screenshots after first load
- CAPTCHAs may still block; residential proxies help
