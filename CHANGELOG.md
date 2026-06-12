# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Oaklight/veilrender/compare/v0.1.0...HEAD
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
