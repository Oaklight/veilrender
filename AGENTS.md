# AGENTS.md — VeilRender

> Context file for AI coding assistants. Symlinked as `CLAUDE.md`.

## What this project is

VeilRender is a **headless browser rendering API** — accepts a URL, renders it
with a stealth Chromium browser (CloakBrowser + Patchright), returns
HTML/Markdown/readability content. Designed as a fallback for fetch tools that
fail on JavaScript-rendered pages.

Supports two deployment modes: **single-instance** (embedded browser) and
**gateway + worker pool** (browser containers scale independently).

Only runtime dependency is `patchright`. Everything else is vendored from
[zerodep](https://github.com/Oaklight/zerodep) — HTTP server, S3 client, HTML
parsing, readability extraction.

## Architecture

### Request flow

```
HTTP request → auth → route handler → browser_manager.get_page()
                                        ↓
                              LocalWorker (embedded CloakBrowser)
                              RemoteWorker (CDP, Chromium)
                              PlaywrightWorker (Playwright protocol, Firefox/Camoufox)
```

### Key components

| Component | File | Purpose |
|-----------|------|---------|
| HTTP server | `_vendor/httpserver` | Async HTTP framework (zerodep) |
| Browser pool | `browser.py` | `LocalWorker`, `RemoteWorker`, `PlaywrightWorker`, `BrowserManager` |
| Config | `config.py` | `VEILRENDER_*` env vars, worker protocol parsing |
| Routes | `routes/*.py` | `/render`, `/screenshot`, `/health`, `/metrics`, `/stats`, `/` dashboard |
| Storage | `storage.py` | L1 TTLCache + L2 S3 (vendored `S3Client`) |
| Filters | `filters.py` | Outbound request blocklist (StevenBlack/hosts) |
| CDP proxy | `cdp_proxy.py` | WebSocket proxy for direct CDP access |
| Stats | `stats.py` | In-memory counters, p50/p95 latency |

### Worker types

| Type | Connection | Browser | Stealth |
|------|-----------|---------|---------|
| `LocalWorker` | Local subprocess | CloakBrowser (auto-downloaded) | Browser-level + driver-level |
| `RemoteWorker` | `chromium.connect_over_cdp()` | Any CDP-compatible Chromium | Driver-level (Patchright) |
| `PlaywrightWorker` | `firefox.connect()` | Camoufox or Playwright-served Firefox | Browser-level (Camoufox) |

## Repository layout

```
src/veilrender/
├── app.py              # HTTP server + CDP WebSocket multiplexing
├── config.py           # Settings from env vars (VEILRENDER_ prefix)
├── auth.py             # Token verification
├── browser.py          # Worker classes + BrowserManager pool coordinator
├── cdp_proxy.py        # CDP WebSocket proxy
├── filters.py          # Outbound request blocklist
├── models.py           # Request/response dataclasses
├── stats.py            # In-memory request counters and latency
├── storage.py          # L1 (TTLCache) + L2 (S3) render cache
├── routes/
│   ├── dashboard.py    # GET / — stats dashboard with i18n (en/zh)
│   ├── health.py       # GET /health
│   ├── metrics.py      # GET /metrics — Prometheus exposition
│   ├── render.py       # POST /render
│   └── screenshot.py   # POST /screenshot
└── _vendor/            # zerodep modules — DO NOT EDIT manually
    ├── httpserver.py    # Async HTTP server
    ├── cache.py         # TTLCache
    ├── s3.py            # S3-compatible client
    ├── readability.py   # Article extraction
    └── soup.py          # HTML parser
deploy/
├── compose.yaml            # Single-instance (prod)
├── compose-dev.yaml        # Dev instance (port 7861)
├── compose-pool.yaml       # Gateway + CloakBrowser workers
├── compose-pool-mixed.yaml # Gateway + CloakBrowser + Camoufox
└── Dockerfile.camoufox     # Camoufox server image
scripts/
└── download-cloakbrowser.py  # Download CloakBrowser binary
```

## Commands

```bash
make dev            # Run dev server on :7860
make build          # Docker build (full target, with CloakBrowser)
make build-gateway  # Docker build (gateway target, no browser)
make run            # Docker run
make lint           # ruff check --fix && ruff format
make typecheck      # ty check
make vendor         # Re-vendor zerodep modules
```

## Deployment

### Dev deployment

```bash
make deploy-dev SSH_TARGET=oaklight.buttercup          # single-instance
make deploy-dev SSH_TARGET=oaklight.buttercup POOL=1   # gateway + workers
```

Builds from the **working tree** (not committed state), tags as `dev-test`,
deploys to `veilrender-dev` stack (port 7861). Always verify no dirty files
in `src/` before deploying.

### Release

1. Update `CHANGELOG.md` — move `[Unreleased]` to `[X.Y.Z]`
2. Bump `__version__` in `src/veilrender/__init__.py`
3. Commit: `git commit -m "bump version to X.Y.Z"`
4. Tag and push: `git tag vX.Y.Z && git push && git push origin vX.Y.Z`
5. Release workflow auto-publishes to PyPI, Docker Hub, GHCR, and creates
   GitHub Release from changelog

### Production

Prod runs on `oaklight.buttercup` at `/dockervol/dockge/stacks/veilrender`
(port 7860), exposed via NPS as `veilrender.service.oaklight.top`.

Update prod to a released version:
```bash
ssh oaklight.buttercup 'cd /dockervol/dockge/stacks/veilrender && \
  docker compose pull && docker compose up -d'
```

## Escalation

- Browser won't start → check `_find_browser_binary()` cascade:
  `CLOAKBROWSER_BINARY` env → `~/.cloakbrowser/*/chrome` → auto-download
- Remote worker won't connect → check `_resolve_to_ip()` (Chromium rejects
  non-IP Host headers), verify CDP port is accessible
- Camoufox worker won't connect → check Playwright version compatibility
  (client/server major.minor must match)
- Vendor module issue → never fix in-place; update upstream zerodep, re-vendor
- Test failure after 3 attempts → stop, report full output
- Never: delete files to fix errors, skip lint, modify `_vendor/` directly

## Files to never edit

- `src/veilrender/_vendor/**` — vendored zerodep modules, update via
  `make vendor` or `zerodep add` from ~/projects/zerodep
- `CLAUDE.md` — symlink to `AGENTS.md`, edit `AGENTS.md` instead

## Definition of done

1. `ruff check --fix && ruff format` on changed Python files
2. `ty check` passes
3. Server starts and `/health` returns 200
4. `/render` returns valid content for a test URL
5. `/metrics` returns valid Prometheus output
