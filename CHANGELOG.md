# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- **Blind SSRF closed with an enforcing egress proxy** — every browser tier sends its HTTP, HTTPS, and WebSocket traffic through an in-process proxy (`egress_proxy.py`). The proxy validates each destination, including redirect hops that Playwright route handlers cannot see, resolves it once, and connects only to the validated address. Non-global destinations are refused with `403` before any connection is made. This also removes the tier-fallback gap where Obscura's built-in private-network block was lost, and closes DNS rebinding for proxied traffic.
- **UDP transports are outside the proxy** — WebRTC/QUIC do not traverse an HTTP proxy. Local Chromium is launched with `--disable-quic` and `--force-webrtc-ip-handling-policy=disable_non_proxied_udp`; remote Chromium workers must be launched with the same flags and Camoufox with `media.peerconnection.ice.proxy_only=true` (or WebRTC disabled), or these tiers need host-level egress rules. The HTTP proxy is not an egress firewall.
- **Special-purpose ranges refused** — multicast, NAT64-encoded IPv4 (`64:ff9b::/96`, `64:ff9b:1::/48`), IPv4-compatible `::/96`, 6to4, Teredo, ORCHID, SRv6, documentation and benchmarking ranges are rejected even where `ipaddress.is_global` reports them as reachable.
- **Remote Obscura workers are verified, not asserted** — `VEILRENDER_OBSCURA_REMOTE_PROXIED=true` is now backed by an HTTP and CONNECT canary at startup, after reconnects, and after restarts: each worker navigates to a `.invalid` host, and the request is refused only if it arrived through the proxy. A worker that ignores its proxy configuration is marked unhealthy instead of serving unprotected. Workers that are not declared proxied are still skipped.
- **`/cdp` disabled by default** — raw CDP clients can create browser contexts outside the proxy. Local Chromium is now also launched with a browser-level `--proxy-server` (and `<-loopback>` bypass), so `/cdp`-created targets are still proxied; enable the endpoint explicitly with `VEILRENDER_CDP_ENABLED=true` and treat it as container-level access. When remote workers are configured, `/cdp` is rejected because the gateway cannot apply that launch-level proxy to them.
- **Upstream DNS rebinding closed by default** — with `VEILRENDER_UPSTREAM_PROXY` set, the validated IP is now sent upstream instead of the hostname (`VEILRENDER_UPSTREAM_PIN_IP` defaults to `true`). Setting it to `false` forwards the hostname and is an explicit trade-off.
- **Strict boolean parsing** — security-relevant `VEILRENDER_*` booleans accept `true/false`, `1/0`, `yes/no`, `on/off`; an empty value means unset, and any other unrecognised value aborts startup instead of silently disabling enforcement.
- **Control characters rejected** — request targets, CONNECT authorities, and forwarded headers containing C0 controls/DEL are refused, and absolute-form targets are rebuilt from parsed components rather than forwarded verbatim.
- **Proxy resource limits** — 10s request-header timeout, 5s DNS timeout, 30s drain timeout, 60s tunnel idle timeout, and a 1024-connection cap, so a slow or non-reading peer cannot pin handlers indefinitely. DNS lookups run on a small dedicated executor with a capped in-flight count, so a stalled resolver cannot occupy the loop's shared default executor.
- **Forwarded `Host` rewritten** — absolute-form requests have their `Host` replaced with the validated authority (and duplicate `Host` lines dropped), so the origin cannot be reached under a virtual host the policy did not check.
- **Canary attestation requires authentication** — when the proxy requires a token, canary requests are only recognised after `Proxy-Authorization` is verified, so an unauthenticated local process cannot forge a worker's attestation.
- **Corrected 0.6.3 changelog** — the route handler does not see redirect hops; the post-navigation URL validation is what stopped the response body from being returned, while the request itself was still issued.

### Upgrading to 0.6.4

The egress proxy is enabled by default and changes how every browser reaches the network. Existing deployments need these changes:

- **Worker pools** must expose the proxy to the worker containers: set `VEILRENDER_EGRESS_BIND=0.0.0.0`, a fixed `VEILRENDER_EGRESS_PORT`, `VEILRENDER_EGRESS_ADVERTISE`, and `VEILRENDER_EGRESS_PROXY_TOKEN`. A worker whose traffic cannot reach the proxy is disabled at startup rather than used unprotected.
- **Remote Obscura** workers must be launched with `--proxy` pointing at the gateway proxy and declared with `VEILRENDER_OBSCURA_REMOTE_PROXIED=true`; otherwise they are not used.
- **Remote Chromium/Camoufox** workers need the UDP launch flags described below (`--disable-quic`, `--force-webrtc-ip-handling-policy=disable_non_proxied_udp`; Camoufox: `media.peerconnection.ice.proxy_only=true`), because UDP does not traverse the HTTP proxy.
- **`/cdp` is disabled by default.** Set `VEILRENDER_CDP_ENABLED=true` if you rely on it.
- `VEILRENDER_EGRESS_PROXY=false` disables enforcement and is not supported for internet-facing deployments.

### Added

- `VEILRENDER_UPSTREAM_PROXY` chains validated traffic through an operator-supplied HTTP, HTTPS, or SOCKS5 proxy; `VEILRENDER_UPSTREAM_PIN_IP` (default `true`) sends the validated IP instead of the hostname. Browser credentials are never exposed to the upstream.
- Egress proxy configuration: `VEILRENDER_EGRESS_BIND`, `VEILRENDER_EGRESS_PORT`, `VEILRENDER_EGRESS_ADVERTISE`, `VEILRENDER_EGRESS_PROXY_TOKEN` (Basic auth, required for non-loopback binds), `VEILRENDER_CDP_ENABLED` (default `false`).
- `/metrics` exposes `veilrender_egress_proxy_enabled`, `_upstream_configured`, `_active_connections`, `_requests_total`, `_blocked_total`, `_canary_blocked_total`, and `_upstream_errors_total`.
- Chromium launch flags `--disable-quic` and `--force-webrtc-ip-handling-policy=disable_non_proxied_udp` for local browsers, keeping UDP-based transports off the direct network path.

### Changed

- Browser contexts are created with a proxy that sets `bypass=<-loopback>`, so Chromium cannot skip the proxy for loopback destinations.

## [0.6.3] - 2026-10-16

### Security

- **SSRF via redirect (response disclosure)** — the URL a navigation actually landed on is now validated before its content is returned. Previously only the submitted URL was validated, so a public URL that redirected to an internal address had the internal response body returned to the caller. Affected `/render` and `/screenshot`. Reported privately by a security researcher; see the published advisory for detail and credit. The browser still issued the redirected request (blind SSRF); that is closed in 0.6.4 by the egress proxy.
- **Non-global addresses rejected** — the address check now uses `is_global` instead of an enumerated private-range denylist, so CGNAT (`100.64.0.0/10`) and other special-purpose ranges are refused rather than fetched.
- **Destination check no longer tied to resource filtering** — the check is installed even when `VEILRENDER_RESOURCE_FILTER=false`. Previously that setting skipped the request filter entirely, which would have removed the destination check along with it.

### Added

- `SECURITY.md` documenting private vulnerability reporting and scope.

## [0.6.2] - 2026-09-24

### Added

- **Partial content capture on timeout** — when `page.goto()` times out on the final render attempt (tier-1 or single-worker), the DOM is captured as-is instead of returning a 502. Useful for JS-heavy SPAs that render meaningful content before `networkidle` fires. Response includes `metadata.partial: true` to signal incomplete capture ([#57], [#59])

### Fixed

- **Browser downloads disabled** — `accept_downloads=False` set on all browser contexts; binary file extensions (`.parquet`, `.zip`, `.tar.gz`, etc.) rejected with 400 before allocating a browser slot; Playwright's "Download is starting" error returns 400 instead of 502 ([#56], [#58])
- **Font URL dynamic resolution** — font download URLs now resolved via GitHub Contents API instead of hardcoded jsDelivr paths. Fixes broken downloads for `noto-color-emoji` (moved + renamed), `noto-sans-arabic/thai/devanagari` (filename changed), and all variable fonts (jsDelivr 403 on large files). Directory listings cached per path; supports `GITHUB_TOKEN` for authenticated API access ([#60])

## [0.6.1] - 2026-09-16

### Added

- **Speculative tier-0 racing** — Obscura gets `VEILRENDER_OBSCURA_TIMEOUT` ms (default 10s) to succeed; if slow, tier-1 starts immediately and the first to finish wins ([#45])
- **Hard request deadline** — `VEILRENDER_REQUEST_DEADLINE` (default 45s) wraps the entire render/screenshot pipeline; returns 504 if exceeded ([#46], [#51])
- **Per-IP rate limiting** — `VEILRENDER_RATE_LIMIT` (e.g. `"10/60"`) uses vendored zerodep sliding-window limiter; returns 429 with `Retry-After` ([#47], [#53])
- **Request queue depth limit** — `VEILRENDER_MAX_QUEUE` caps waiting requests; returns 503 when overloaded ([#48], [#52])
- **CDP proxy tier routing** — `/cdp` defaults to tier-1 (CloakBrowser) for full Chromium compatibility; `?tier=0` opts into Obscura ([#50], [#51])
- `ObscuraWorker.force_wait_until = "load"` — forces Obscura to use `load` instead of `networkidle` to prevent CDP hangs ([#45])
- Stuck worker detection — health loop detects workers with stale active slot count for >2× timeout and force-restarts them ([#45])
- `WaitUntil` type alias for Playwright's `wait_until` parameter ([#45])
- Test release workflow (`test-release.yml`) for TestPyPI + dev Docker images
- Vendored zerodep `ratelimit` module (sliding window, token bucket, GCRA) ([#53])

### Fixed

- **Semaphore slot leaks** — `asyncio.shield` prevented cancellation of tier-0 tasks; replaced with direct cancel + fire-and-forget for unresponsive Obscura CDP
- Stuck detection only triggered on full occupancy (all slots); now triggers on any stale active count
- **Full-page screenshot timeout** — reserved navigation timeout budget for the capture step; explicit screenshot timeout derived from remaining deadline ([#54])
- **Font CSS pipeline** — replaced 7 external CDN fetches per screenshot with locally cached inline CSS; font URLs rewritten to local `/fonts/fontsource/` endpoint; `@font-face` rules deduplicated across scripts; multi-CDN racing (jsDelivr, unpkg, esm.sh) for initial download

### Changed

- `BrowserManager.get_cdp_url()` gains `min_tier` parameter (default 1) ([#50])
- `BrowserManager.get_page()` yields 4-tuple `(ctx, page, engine_label, force_wait_until)` ([#45])
- Render/screenshot pipeline extracted into `_render_pipeline()` / `_screenshot_pipeline()` for deadline wrapping ([#46])
- Font injection uses `add_style_tag(content=...)` instead of `add_style_tag(url=...)` — no external network during screenshots

## [0.6.0] - 2026-09-15

### Added

- **Obscura headless browser** as tier-0 worker — lightweight Rust-based browser (~30MB memory, ~85ms page loads) with built-in stealth, auto-downloaded from GitHub releases ([#41], [#42])
- **Two-tier fallback system** — try Obscura first (tier 0), automatically fall back to CloakBrowser/Camoufox (tier 1) on failure ([#41], [#42])
- `ObscuraWorker` class with local subprocess management, CDP connection, and auto-restart ([#42])
- Tier system: `_BaseWorker.tier` attribute, tier-aware `_pick_worker()` dispatch preferring lowest available tier ([#42])
- `obscura://` protocol prefix for remote Obscura workers in pool mode ([#42])
- `VEILRENDER_OBSCURA=true` env var to enable local two-tier mode ([#42])
- `VEILRENDER_OBSCURA_MAX_CONCURRENT` for independent Obscura concurrency limits ([#44])
- Configurable `X-Render-Engine` response header with opaque engine labels (`alpha`/`beta`), enabled via `VEILRENDER_ENGINE_HEADER=true` ([#43])
- Per-tier ring gauges on dashboard — shows independent capacity for each tier when multiple tiers are configured ([#44])
- `BrowserManager.tier_stats()` for aggregated per-tier metrics in `/stats` JSON API ([#44])
- `scripts/download-obscura.py` for build-time binary download ([#42])
- `OBSCURA_BINARY`, `OBSCURA_MIRROR`, `OBSCURA_VERSION` env vars for binary management ([#42])

### Changed

- `BrowserManager.get_page()` yields 3-tuple `(ctx, page, engine_label)` instead of 2-tuple ([#43])
- Dashboard metrics layout changed from CSS grid to flexbox to support variable number of ring gauges ([#44])
- Dockerfile `full` target downloads both CloakBrowser and Obscura binaries ([#42])
- `tarfile.extractall()` calls use `filter='data'` to mitigate CVE-2007-4559 path traversal ([#42])

## [0.5.1] - 2026-09-09

### Changed

- Bump vendored httpserver 0.2.1→0.4.0: adds lifespan hooks, cookie support, `State` namespace, `StreamingResponse` background callbacks, thread-safe shutdown ([#38])
- Refactor browser lifecycle to use `@app.on_startup` / `@app.on_shutdown` lifespan hooks instead of manual management in server loop ([#39], [#40])

## [0.5.0] - 2026-08-26

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

[Unreleased]: https://github.com/Oaklight/veilrender/compare/v0.6.2...HEAD
[0.6.2]: https://github.com/Oaklight/veilrender/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/Oaklight/veilrender/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/Oaklight/veilrender/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/Oaklight/veilrender/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/Oaklight/veilrender/compare/v0.4.1...v0.5.0
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
[#30]: https://github.com/Oaklight/veilrender/issues/30
[#38]: https://github.com/Oaklight/veilrender/pull/38
[#39]: https://github.com/Oaklight/veilrender/issues/39
[#40]: https://github.com/Oaklight/veilrender/pull/40
[#41]: https://github.com/Oaklight/veilrender/issues/41
[#42]: https://github.com/Oaklight/veilrender/pull/42
[#43]: https://github.com/Oaklight/veilrender/pull/43
[#44]: https://github.com/Oaklight/veilrender/pull/44
[#45]: https://github.com/Oaklight/veilrender/pull/45
[#46]: https://github.com/Oaklight/veilrender/issues/46
[#47]: https://github.com/Oaklight/veilrender/issues/47
[#48]: https://github.com/Oaklight/veilrender/issues/48
[#50]: https://github.com/Oaklight/veilrender/issues/50
[#51]: https://github.com/Oaklight/veilrender/pull/51
[#52]: https://github.com/Oaklight/veilrender/pull/52
[#53]: https://github.com/Oaklight/veilrender/pull/53
[#54]: https://github.com/Oaklight/veilrender/pull/54
[#56]: https://github.com/Oaklight/veilrender/issues/56
[#57]: https://github.com/Oaklight/veilrender/issues/57
[#58]: https://github.com/Oaklight/veilrender/pull/58
[#59]: https://github.com/Oaklight/veilrender/pull/59
[#60]: https://github.com/Oaklight/veilrender/pull/60
