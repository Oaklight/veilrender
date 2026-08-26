# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `/screenshot` endpoint: `format`, `quality`, `scale`, `selector`, `clip`, `color_scheme`, `wait_for`, `transparent` parameters ([#30])

## [0.4.1] - 2026-08-25

### Fixed

- Readability extraction always returned `null` — vendored `readability` module failed to import sibling `soup` module in flat vendor layout ([#29])

### Changed

- Bump vendored readability 0.2.0→0.2.1 (upstream fix for flat sibling imports)

## [0.4.0] - 2026-08-24

### Added

- **Remote browser worker pool** for horizontal scaling — `VEILRENDER_WORKERS` env var routes requests to remote CDP endpoints via least-connections routing ([#25])
- **Firefox/Camoufox worker support** — `playwright://` protocol prefix for connecting to Playwright-compatible browsers (Camoufox, etc.) alongside CDP workers ([#27])
- `LocalWorker` / `RemoteWorker` / `PlaywrightWorker` abstraction with shared `_BaseWorker` interface ([#25], [#27])
- Worker health checks with automatic reconnection for remote workers ([#25])
- CDP proxy `?worker=N` query param for targeted worker routing ([#25])
- Per-worker Prometheus gauges: `veilrender_worker_healthy`, `veilrender_worker_active_pages`, `veilrender_worker_browser_pages` ([#25])
- Real browser page count via CDP `/json` endpoint for accurate capacity reporting ([#25])
- Prometheus metrics endpoint at `GET /metrics` — zero-dependency exposition format with uptime, browser status, active pages, request counters, cache lookups, and latency summaries (p50/p95) ([#23])
- Dashboard i18n: language selector dropdown (en/zh) with localStorage persistence; extensible via dict — adding a language only requires a new entry ([#22])
- Dashboard `GET /stats` JSON API for live data polling ([#22])
- SVG ring gauge for capacity visualization on dashboard ([#22])
- Author credit and badges in dashboard footer ([#22])
- Multi-target Dockerfile: `gateway` (336MB, no browser) and `full` (1.07GB, CloakBrowser embedded)
- `deploy/compose.yaml` (single-instance), `deploy/compose-pool.yaml` (Chromium pool), `deploy/compose-pool-mixed.yaml` (Chromium + Camoufox mixed pool)
- `deploy/Dockerfile.camoufox` for Camoufox server worker image ([#27])
- `POOL=1` flag for `make deploy-dev` to deploy in pool mode
- `CLOAKBROWSER_MIRROR` env var for China downloads (e.g. `https://ghfast.top`)
- `CLOAKBROWSER_BINARY` env var to use a custom browser binary path
- Auto-download CloakBrowser binary from GitHub Releases without pip package
- `scripts/download-cloakbrowser.py` for standalone binary download

### Changed

- **Migrate from Playwright to Patchright** — drop-in replacement with stealth driver patches for Chromium ([#25])
- **Replace `minio` with vendored zerodep `S3Client`** — only `patchright` remains as runtime dependency ([#27])
- Remove `cloakbrowser` pip dependency — binary downloaded directly from GitHub Releases, stealth args generated inline
- Prune 8 unused vendor modules (368K → 184K): config, dotenv, yaml, jsonx, markdown, structlog, useragent, retry ([#27])
- Docker image size: full 1.43GB → 1.07GB, gateway 498MB → 336MB (removed playwright transitive dep + multi-stage libgbm extraction)
- Dashboard redesign: dark theme inspired by modal.com — pure black background, mint-green accents, DM Sans + JetBrains Mono typography ([#22])
- Dashboard data refresh: replaced `<meta http-equiv="refresh">` full-page reload with fetch-based polling — no more flashing or scroll reset ([#22])
- Dashboard shows stale-data indicator (dims) after 3 consecutive fetch failures ([#22])
- Dashboard pauses polling on hidden tab via Page Visibility API ([#22])
- Shields.io badges use unified dark-green theme colors ([#22])
- Vendored modules: replace deprecated `jsonc` with `jsonx`, remove `benchmark_compare` ([#22])
- Bump vendored config 0.3.0→0.3.1, httpserver 0.1.0→0.2.1, readability 0.1.0→0.2.0
- New config: `VEILRENDER_WORKERS`, `VEILRENDER_WORKER_MAX_CONCURRENT`, `VEILRENDER_WORKER_HEALTH_INTERVAL` ([#25])

### Removed

- HF Spaces badge (space was taken down) ([#22])
- `cloakbrowser` pip dependency (binary auto-downloaded instead)
- `minio` pip dependency (replaced by vendored S3Client) ([#27])

## [0.3.1] - 2026-07-04

### Added

- URL validation before rendering: only `http://` and `https://` schemes allowed; `file://`, `data:`, `javascript:` blocked
- DNS resolution with private IP blocking: loopback, RFC1918, link-local, cloud metadata (169.254.x.x) all rejected — prevents SSRF
- Fail2ban-style IP rate limiting: 3 auth failures in 5 minutes → 10 minute ban, with `X-Forwarded-For` support

### Changed

- Reduce `max_body_size` from 10 MB to 64 KB — render/screenshot payloads are small JSON
- Promote blocked-request filter log from DEBUG to INFO for production visibility

### Fixed

- **CRITICAL**: SSRF via `file:///etc/passwd` — Playwright `page.goto()` accepted arbitrary schemes
- **CRITICAL**: SSRF via `http://127.0.0.1:9222` — CDP debug endpoint exposed WebSocket URLs enabling RCE
- **CRITICAL**: No URL validation — user-supplied URLs forwarded to Playwright without sanitization
- **MEDIUM**: `data:` URLs accepted — attacker could render arbitrary HTML content

## [0.3.0] - 2026-06-26

### Added

- Outbound request filtering using [StevenBlack/hosts](https://github.com/StevenBlack/hosts) community blocklist (~82k ad/tracker/malware domains), blocking at the Playwright level via `page.route()` ([#21])
- Two-tier render cache: L1 in-memory `TTLCache` + L2 S3-compatible persistent storage via `minio` client — supports Cloudflare R2, Oracle Object Storage, AWS S3, etc. ([#21])
- L2 TTL enforcement via embedded `_stored_at` timestamp, checked on read
- S3 lifecycle rule auto-set on startup (7× TTL expiry as bulk cleanup safety net)
- `make update-blocklist` target to refresh blocklist from jsDelivr CDN
- New env vars: `VEILRENDER_RESOURCE_FILTER`, `VEILRENDER_CACHE_ENABLED`, `VEILRENDER_CACHE_TTL`, `VEILRENDER_S3_ENDPOINT`, etc.

## [0.2.0] - 2026-06-13

### Added

- Stats dashboard at `GET /` with badges, capacity bar, and responsive layout ([#20])
- Public HF Space (no auth) with live demo badge
- `.dockerignore` and Docker safety CI

### Changed

- Bump default `max_concurrent` from 3 to 5
- Pre-download Chromium as runtime user to avoid re-download on startup

### Fixed

- HF Space deploy: delete symlink before writing README
- Pre-commit formatting for dashboard.py

## [0.1.0] - 2026-06-12

### Added

- Core rendering API with three endpoints:
  - `POST /render` — URL → rendered HTML / Markdown / readability-extracted text
  - `POST /screenshot` — URL → PNG screenshot
  - `GET /health` — liveness check
- CDP WebSocket proxy at `/cdp` for direct browser control ([#3])
- Token-based authentication via `Authorization: Bearer` header or `?token=` query param
- Per-request browser context isolation with configurable concurrency (`VEILRENDER_MAX_CONCURRENT`)
- [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) integration — stealth Chromium with 58 source-level anti-fingerprint patches ([#14], [#15])
- 13 vendored [zerodep](https://github.com/Oaklight/zerodep) modules — only external dependency is `cloakbrowser`
- Docker image based on `python:3.12-slim` with multi-arch support (amd64/arm64)
- GitHub CI pipeline: pre-commit (ruff + ty), Docker build to GHCR + Docker Hub, auto-deploy to HF Spaces
- PyPI publishing on tag push
- `Makefile` with `deploy-dev` (VPS) and `deploy-hf` (HF Spaces) targets
- Bilingual README (en/zh)

### Fixed

- CDP proxy: preserve FIN bit during WebSocket frame forwarding ([#4], [#12])
- HTTP multiplexer: pipe remaining POST body data instead of `feed_eof()` ([#5], [#9])
- CDP proxy: add 16 MB max frame size limit to prevent OOM ([#6], [#10])
- CDP proxy: cancel both directions when one side closes ([#7], [#11])
- CDP proxy: use random WebSocket key per connection and forward `Sec-WebSocket-Protocol` ([#8], [#13])
- Docker: use `CLOAKBROWSER_CACHE_DIR` so build-time binary download is available at runtime ([#16], [#17])
- Launch Chromium directly via `subprocess.Popen` + `connect_over_cdp()` instead of Playwright's `launch()`, which overrides `--remote-debugging-port`

[Unreleased]: https://github.com/Oaklight/veilrender/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/Oaklight/veilrender/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/Oaklight/veilrender/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Oaklight/veilrender/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Oaklight/veilrender/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Oaklight/veilrender/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Oaklight/veilrender/releases/tag/v0.1.0

[#1]: https://github.com/Oaklight/veilrender/issues/1
[#2]: https://github.com/Oaklight/veilrender/issues/2
[#3]: https://github.com/Oaklight/veilrender/issues/3
[#4]: https://github.com/Oaklight/veilrender/issues/4
[#5]: https://github.com/Oaklight/veilrender/issues/5
[#6]: https://github.com/Oaklight/veilrender/issues/6
[#7]: https://github.com/Oaklight/veilrender/issues/7
[#8]: https://github.com/Oaklight/veilrender/issues/8
[#9]: https://github.com/Oaklight/veilrender/pull/9
[#10]: https://github.com/Oaklight/veilrender/pull/10
[#11]: https://github.com/Oaklight/veilrender/pull/11
[#12]: https://github.com/Oaklight/veilrender/pull/12
[#13]: https://github.com/Oaklight/veilrender/pull/13
[#14]: https://github.com/Oaklight/veilrender/issues/14
[#15]: https://github.com/Oaklight/veilrender/pull/15
[#16]: https://github.com/Oaklight/veilrender/issues/16
[#17]: https://github.com/Oaklight/veilrender/pull/17
[#20]: https://github.com/Oaklight/veilrender/pull/20
[#21]: https://github.com/Oaklight/veilrender/pull/21
[#22]: https://github.com/Oaklight/veilrender/pull/22
[#23]: https://github.com/Oaklight/veilrender/pull/23
[#25]: https://github.com/Oaklight/veilrender/pull/25
[#27]: https://github.com/Oaklight/veilrender/pull/27
[#29]: https://github.com/Oaklight/veilrender/issues/29
