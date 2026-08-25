---
title: Changelog
---

# Changelog

All notable changes to VeilRender are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] — 2026-08-24

### Added

- **Remote browser worker pool** for horizontal scaling — `VEILRENDER_WORKERS` env var routes requests to remote CDP endpoints via least-connections routing
- **Firefox/Camoufox worker support** — `playwright://` protocol prefix for connecting to Playwright-compatible browsers alongside CDP workers
- `LocalWorker` / `RemoteWorker` / `PlaywrightWorker` abstraction with shared `_BaseWorker` interface
- Worker health checks with automatic reconnection for remote workers
- CDP proxy `?worker=N` query param for targeted worker routing
- Per-worker Prometheus gauges: `veilrender_worker_healthy`, `veilrender_worker_active_pages`, `veilrender_worker_browser_pages`
- Real browser page count via CDP `/json` endpoint for accurate capacity reporting
- Prometheus metrics endpoint at `GET /metrics` — zero-dependency exposition format with uptime, browser status, active pages, request counters, cache lookups, and latency summaries (p50/p95)
- Dashboard i18n: language selector dropdown (en/zh) with localStorage persistence
- Dashboard `GET /stats` JSON API for live data polling
- SVG ring gauge for capacity visualization on dashboard
- Multi-target Dockerfile: `gateway` (336 MB, no browser) and `full` (1.07 GB, CloakBrowser embedded)
- Compose files: `deploy/compose.yaml` (single-instance), `deploy/compose-pool.yaml` (Chromium pool), `deploy/compose-pool-mixed.yaml` (Chromium + Camoufox mixed pool)
- `deploy/Dockerfile.camoufox` for Camoufox server worker image
- `CLOAKBROWSER_MIRROR` env var for China downloads (e.g. `https://ghfast.top`)
- `CLOAKBROWSER_BINARY` env var to use a custom browser binary path
- Auto-download CloakBrowser binary from GitHub Releases without pip package

### Changed

- **Migrate from Playwright to Patchright** — drop-in replacement with stealth driver patches for Chromium
- **Replace `minio` with vendored zerodep `S3Client`** — only `patchright` remains as runtime dependency
- Remove `cloakbrowser` pip dependency — binary downloaded directly from GitHub Releases
- Docker image size: full 1.43 GB → 1.07 GB, gateway 498 MB → 336 MB
- Dashboard redesign: dark theme — pure black background, mint-green accents, DM Sans + JetBrains Mono typography
- Dashboard data refresh: fetch-based polling replaces full-page reload (no more flashing or scroll reset)

### Removed

- HF Spaces public demo badge (space was taken down)
- `cloakbrowser` pip dependency (binary auto-downloaded instead)
- `minio` pip dependency (replaced by vendored S3Client)

## [0.3.1] — 2026-07-04

### Added

- URL validation: only `http://` and `https://` schemes allowed; `file://`, `data:`, `javascript:` blocked
- DNS resolution with private IP blocking: loopback, RFC1918, link-local, cloud metadata (169.254.x.x) rejected — prevents SSRF
- Fail2ban-style IP rate limiting: 3 auth failures in 5 minutes → 10-minute ban, with `X-Forwarded-For` support

### Changed

- Reduce `max_body_size` from 10 MB to 64 KB

### Fixed

- **CRITICAL**: SSRF via `file:///etc/passwd` — Playwright `page.goto()` accepted arbitrary schemes
- **CRITICAL**: SSRF via `http://127.0.0.1:9222` — CDP debug endpoint exposed WebSocket URLs enabling RCE
- **CRITICAL**: No URL validation — user-supplied URLs forwarded to Playwright without sanitization
- **MEDIUM**: `data:` URLs accepted — attacker could render arbitrary HTML content

## [0.3.0] — 2026-06-26

### Added

- Outbound request filtering using [StevenBlack/hosts](https://github.com/StevenBlack/hosts) community blocklist (~82k ad/tracker/malware domains), blocking at the Playwright level via `page.route()`
- Two-tier render cache: L1 in-memory `TTLCache` + L2 S3-compatible persistent storage — supports Cloudflare R2, Oracle Object Storage, AWS S3, etc.
- L2 TTL enforcement via embedded `_stored_at` timestamp, checked on read
- S3 lifecycle rule auto-set on startup (7× TTL expiry as bulk cleanup safety net)
- New env vars: `VEILRENDER_RESOURCE_FILTER`, `VEILRENDER_CACHE_ENABLED`, `VEILRENDER_CACHE_TTL`, `VEILRENDER_S3_ENDPOINT`, etc.

## [0.2.0] — 2026-06-13

### Added

- Stats dashboard at `GET /` with badges, capacity bar, and responsive layout
- Public HF Space (no auth) with live demo badge

### Changed

- Bump default `max_concurrent` from 3 to 5
- Pre-download Chromium as runtime user to avoid re-download on startup

## [0.1.0] — 2026-06-12

### Added

- Core rendering API: `POST /render`, `POST /screenshot`, `GET /health`
- CDP WebSocket proxy at `/cdp` for direct browser control
- Token-based authentication via `Authorization: Bearer` header
- Per-request browser context isolation with configurable concurrency
- [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) integration — stealth Chromium with fingerprint patches
- 13 vendored [zerodep](https://github.com/Oaklight/zerodep) modules — minimal external dependencies
- Docker image with multi-arch support (amd64/arm64)
- GitHub CI pipeline: pre-commit, Docker build, auto-deploy
- PyPI publishing on tag push
- Bilingual README (en/zh)

[0.4.0]: https://github.com/Oaklight/veilrender/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Oaklight/veilrender/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Oaklight/veilrender/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Oaklight/veilrender/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Oaklight/veilrender/releases/tag/v0.1.0
