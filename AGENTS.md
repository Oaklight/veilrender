# AGENTS.md — VeilRender

> Context file for AI coding assistants. Symlinked as `CLAUDE.md`.

## What this project is

VeilRender is a **headless browser rendering API** — accepts a URL, renders it
with a stealth browser, returns HTML/Markdown/readability content. Designed as
a fallback for fetch tools that fail on JavaScript-rendered pages.

Uses a **two-tier worker system**: lightweight Obscura (Rust, ~30MB) as tier-0
for fast renders, falling back to CloakBrowser/Camoufox (full Chromium/Firefox)
as tier-1 when Obscura can't handle a page.

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
                              tier 0: ObscuraWorker (embedded Obscura, Rust)
                                ↓ (fallback on failure)
                              tier 1: LocalWorker (embedded CloakBrowser)
                                      RemoteWorker (CDP, Chromium)
                                      PlaywrightWorker (Playwright protocol, Firefox/Camoufox)
```

### Egress enforcement

Every browser context is pointed at an in-process HTTP proxy
(`egress_proxy.py`) listening on loopback. The proxy sees each connection the
browser opens — including redirect hops, which `page.route` does not
intercept — and:

- resolves the destination once and requires every result to be globally
  routable (`is_global`),
- connects to a validated address and never re-resolves, so DNS rebinding
  cannot move the connection,
- refuses anything else with `403` before connecting.

Obscura ignores per-context proxy settings, so it is started with `--proxy`.
If the proxy is unreachable, browser requests fail: there is no unprotected
path, and tier fallback cannot drop the policy.

An operator-supplied proxy can be chained in front of the public internet with
`VEILRENDER_UPSTREAM_PROXY`; destinations are still validated locally before
anything is forwarded, and the validated IP (not the hostname) is sent
upstream unless `VEILRENDER_UPSTREAM_PIN_IP=false` explicitly opts out.

At startup, after a reconnect, and after a worker restart, each worker runs
HTTP and CONNECT canary navigations to a `.invalid` host. The proxy refuses
each token on receipt, before DNS, so a worker that ignores its proxy
configuration is marked unhealthy rather than used unprotected. The
destination policy also refuses multicast, NAT64-encoded IPv4
(`64:ff9b::/96`), 6to4/Teredo, and the other special-purpose ranges that
`ipaddress.is_global` reports as reachable.

The `/cdp` endpoint is **disabled by default** (`VEILRENDER_CDP_ENABLED=true`
to opt in): raw CDP clients can create browser contexts outside the proxy.
Local Chromium is additionally launched with a browser-level `--proxy-server`,
so targets created over `/cdp` still route through the proxy. When remote
workers are configured, `/cdp` is rejected because the gateway cannot apply
that launch-level proxy to them.

Boolean `VEILRENDER_*` variables accept `true/false`, `1/0`, `yes/no`, and
`on/off`. An empty value means unset (the default); any other value aborts
startup, so a typo cannot silently disable enforcement.

### Key components

| Component | File | Purpose |
|-----------|------|---------|
| HTTP server | `_vendor/httpserver` | Async HTTP framework (zerodep) |
| Browser pool | `browser.py` | `ObscuraWorker`, `LocalWorker`, `RemoteWorker`, `PlaywrightWorker`, `BrowserManager` |
| Config | `config.py` | `VEILRENDER_*` env vars, worker protocol parsing |
| Routes | `routes/*.py` | `/render`, `/screenshot`, `/health`, `/metrics`, `/stats`, `/` dashboard |
| Storage | `storage.py` | L1 TTLCache + L2 S3 (vendored `S3Client`) |
| Filters | `filters.py` | Outbound request blocklist (StevenBlack/hosts) |
| Egress proxy | `egress_proxy.py` | Enforcing HTTP proxy — validates every connection target, including redirect hops |
| CDP proxy | `cdp_proxy.py` | WebSocket proxy for direct CDP access |
| Stats | `stats.py` | In-memory counters, p50/p95 latency |

### Worker types

| Type | Tier | Connection | Browser | Stealth |
|------|------|-----------|---------|---------|
| `ObscuraWorker` | 0 | Local subprocess | Obscura (auto-downloaded Rust binary) | Built-in (V8 + TLS fingerprint) |
| `LocalWorker` | 1 | Local subprocess | CloakBrowser (auto-downloaded) | Browser-level + driver-level |
| `RemoteWorker` | 1 | `chromium.connect_over_cdp()` | Any CDP-compatible Chromium | Driver-level (Patchright) |
| `PlaywrightWorker` | 1 | `firefox.connect()` | Camoufox or Playwright-served Firefox | Browser-level (Camoufox) |

### Deployment modes

| Mode | Config | Workers |
|------|--------|---------|
| Single CloakBrowser (default) | No extra env vars | `LocalWorker` (tier 1) |
| Two-tier local | `VEILRENDER_OBSCURA=true` | `ObscuraWorker` (tier 0) + `LocalWorker` (tier 1) |
| Pool with Obscura | `VEILRENDER_WORKERS=obscura://obs:9223,cdp://chrome:9222` | Remote Obscura (tier 0) + Remote Chrome (tier 1) |
| Pool mixed | `VEILRENDER_WORKERS=obscura://obs:9223,cdp://chrome:9222,playwright://fox:1234/ws` | Obscura + Chrome + Camoufox |

In pool mode the workers run in separate containers and cannot reach the
gateway's loopback. Bind the egress proxy to a container-network address,
advertise it, and require authentication:

```bash
VEILRENDER_EGRESS_BIND=0.0.0.0
VEILRENDER_EGRESS_PORT=7870
VEILRENDER_EGRESS_ADVERTISE=http://<gateway-service>:7870
VEILRENDER_EGRESS_PROXY_TOKEN=<random-secret>
```

Remote Obscura workers are not used unless they were started with `--proxy`
pointing at this proxy and `VEILRENDER_OBSCURA_REMOTE_PROXIED=true` is set.

### Environment variables

#### Obscura / tier system

| Variable | Default | Description |
|----------|---------|-------------|
| `VEILRENDER_OBSCURA` | `false` | Enable local Obscura (tier 0) + CloakBrowser (tier 1) two-tier mode |
| `VEILRENDER_OBSCURA_MAX_CONCURRENT` | `VEILRENDER_MAX_CONCURRENT` | Max concurrent pages for Obscura (tier 0); independent of tier-1 limit |
| `VEILRENDER_ENGINE_HEADER` | `false` | Include opaque `X-Render-Engine` header in responses (`alpha` = tier 0, `beta` = tier 1) |
| `VEILRENDER_OBSCURA_REMOTE_PROXIED` | `false` | Declare that remote Obscura workers were started with `--proxy` pointing at this instance; otherwise they are not used |
| `OBSCURA_BINARY` | — | Path to Obscura binary (skips auto-download) |
| `OBSCURA_VERSION` | `0.2.2` | Obscura version to auto-download |
| `OBSCURA_MIRROR` | — | URL prefix for Obscura download mirror |

#### Core

| Variable | Default | Description |
|----------|---------|-------------|
| `VEILRENDER_API_TOKEN` | — | Bearer token for authentication |
| `VEILRENDER_PORT` | `7860` | Server listen port |
| `VEILRENDER_MAX_CONCURRENT` | `5` | Max concurrent pages for tier-1 workers (CloakBrowser) |
| `VEILRENDER_TIMEOUT` | `30000` | Default navigation timeout (ms) |
| `VEILRENDER_WORKERS` | — | Remote worker pool (comma-separated: `cdp://`, `playwright://`, `obscura://`) |
| `VEILRENDER_RESOURCE_FILTER` | `true` | Enable outbound request blocklist |
| `VEILRENDER_EGRESS_PROXY` | `true` | Enforce the outbound destination policy through the in-process proxy |
| `VEILRENDER_EGRESS_BIND` | `127.0.0.1` | Address the egress proxy binds to |
| `VEILRENDER_EGRESS_PORT` | `0` | Proxy port; `0` = ephemeral. Set a fixed port when remote workers must reach it |
| `VEILRENDER_EGRESS_ADVERTISE` | — | URL browsers use to reach the proxy (e.g. `http://gateway:7870`); required for workers in other containers |
| `VEILRENDER_EGRESS_PROXY_TOKEN` | — | Basic-auth password for the proxy; required when the bind address is not loopback |
| `VEILRENDER_UPSTREAM_PROXY` | — | Chain validated traffic through an `http`, `https`, or `socks5` upstream proxy |
| `VEILRENDER_UPSTREAM_PIN_IP` | `true` | Send the validated IP (not the hostname) to the upstream proxy; `false` lets the upstream resolve again |
| `VEILRENDER_CDP_ENABLED` | `false` | Enable the raw `/cdp` WebSocket endpoint. Raw CDP can create contexts that bypass the proxy, so only enable it for trusted operators |
| `CLOAKBROWSER_BINARY` | — | Path to CloakBrowser binary (skips auto-download) |
| `CLOAKBROWSER_MIRROR` | — | URL prefix for CloakBrowser download mirror |

## Repository layout

```
src/veilrender/
├── app.py              # HTTP server + CDP WebSocket multiplexing
├── config.py           # Settings from env vars (VEILRENDER_ prefix)
├── auth.py             # Token verification
├── browser.py          # Worker classes + BrowserManager pool coordinator
├── cdp_proxy.py        # CDP WebSocket proxy
├── filters.py          # Outbound request blocklist
├── egress_proxy.py     # Enforcing egress proxy (destination validation)
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
├── compose-dev.yaml        # Dev instance (port 7861, Obscura + CloakBrowser)
├── compose-pool.yaml       # Gateway + CloakBrowser workers
├── compose-pool-mixed.yaml # Gateway + Obscura + CloakBrowser + Camoufox
└── Dockerfile.camoufox     # Camoufox server image
scripts/
├── download-cloakbrowser.py  # Download CloakBrowser binary
└── download-obscura.py       # Download Obscura binary
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

- Obscura won't start → check `_find_obscura_binary()` cascade:
  `OBSCURA_BINARY` env → `~/.obscura/*/obscura` → auto-download
- CloakBrowser won't start → check `_find_browser_binary()` cascade:
  `CLOAKBROWSER_BINARY` env → `~/.cloakbrowser/*/chrome` → auto-download
- Remote worker won't connect → check `_resolve_to_ip()` (Chromium rejects
  non-IP Host headers), verify CDP port is accessible
- Camoufox worker won't connect → check Playwright version compatibility
  (client/server major.minor must match)
- Browser navigations fail with proxy or tunnel errors → check the egress
  proxy log line at startup; for pool mode verify `VEILRENDER_EGRESS_ADVERTISE`,
  the bind address, and `VEILRENDER_EGRESS_PROXY_TOKEN`
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
