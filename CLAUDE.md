# CLAUDE.md — VeilRender

## What this project is

Headless browser rendering API. Accepts a URL, renders it with Patchright +
CloakBrowser (stealth Chromium), returns HTML/Markdown/readability content.
Supports single-instance and gateway+worker pool deployment modes.

## Architecture

- **Zero external deps** except `patchright` — uses vendored `zerodep` modules
  in `src/veilrender/_vendor/` for HTTP server, HTML parsing, readability, etc.
- **`httpserver`** (zerodep) as the async HTTP framework — not FastAPI
- **Patchright** (stealth Playwright fork) for browser control via CDP
- **CloakBrowser** stealth Chromium binary — auto-downloaded, no pip package needed
- **Stateless** — no session management, no database
- **Two deployment modes**:
  - **Full** (single-instance): embedded CloakBrowser, 1.07GB image
  - **Gateway + Workers** (pool): gateway routes to remote `cloakhq/cloakbrowser` CDP workers, 336MB gateway image

## Repository layout

```
src/veilrender/
├── app.py          # HTTP server setup, route registration, main()
├── config.py       # Settings from env vars (VEILRENDER_ prefix)
├── auth.py         # Token verification
├── browser.py      # Browser lifecycle: LocalWorker, RemoteWorker, BrowserManager pool
├── filters.py      # Outbound request blocklist filtering
├── models.py       # Request/response dataclasses
├── routes/
│   ├── dashboard.py  # GET / — stats dashboard with i18n
│   ├── health.py     # GET /health — liveness check
│   ├── metrics.py    # GET /metrics — Prometheus exposition format
│   ├── render.py     # POST /render — URL → HTML/Markdown/readability
│   └── screenshot.py # POST /screenshot — URL → PNG
├── stats.py        # In-memory request counters and latency tracking
└── _vendor/        # zerodep modules — DO NOT EDIT manually
deploy/
├── compose.yaml       # Single-instance Docker Compose
└── compose-pool.yaml  # Gateway + CloakBrowser worker pool
scripts/
└── download-cloakbrowser.py  # Download CloakBrowser binary (no pip needed)
```

## Commands

```bash
make dev            # Run dev server on :7860
make build          # Docker build (full, with CloakBrowser)
make build-gateway  # Docker build (gateway only, no browser)
make run            # Docker run
make lint           # ruff check --fix && ruff format
make typecheck      # ty check
make vendor         # Re-vendor zerodep modules
make deploy-dev SSH_TARGET=host          # Deploy single-instance
make deploy-dev SSH_TARGET=host POOL=1   # Deploy gateway + worker pool
```

## Environment variables

### Core
- `VEILRENDER_API_TOKEN` — Bearer token for auth
- `VEILRENDER_PORT` — Listen port (default 7860)
- `VEILRENDER_MAX_CONCURRENT` — Max concurrent pages (default 5)
- `VEILRENDER_TIMEOUT` — Page load timeout in ms (default 30000)

### Worker pool
- `VEILRENDER_WORKERS` — Comma-separated remote CDP endpoints (enables pool mode)
- `VEILRENDER_WORKER_MAX_CONCURRENT` — Per-worker concurrency limit
- `VEILRENDER_WORKER_HEALTH_INTERVAL` — Health check interval in seconds (default 10)

### Browser binary
- `CLOAKBROWSER_BINARY` — Path to custom browser binary
- `CLOAKBROWSER_MIRROR` — GitHub mirror for China downloads (e.g. `https://ghfast.top`)

## Files to never edit

- `src/veilrender/_vendor/**` — vendored zerodep modules, update via
  `zerodep update` from ~/projects/zerodep

## Definition of done

1. `ruff check --fix && ruff format` on changed Python files
2. Server starts and `/health` returns 200
3. `/render` returns valid content for a test URL
4. `/metrics` returns valid Prometheus output
