---
title: Changelog
---

# Changelog

## v0.2.0

- **feat**: Stats dashboard at `GET /` with badges, capacity bar, and responsive layout
- **feat**: Public HF Space (no auth) with live demo badge
- **improve**: Bump default `max_concurrent` from 3 to 5
- **fix**: Pre-download Chromium as runtime user to avoid re-download on startup
- **infra**: Split CI workflows into ci, release, and deploy-hf
- **infra**: Add PyPI publish workflow, Docker Hub / GHCR multi-arch images
- **infra**: Add benchmark results

## v0.1.0

- Initial release: headless browser rendering API
- `POST /render` — render URL to HTML, Markdown, readability
- `POST /screenshot` — capture page screenshots
- `GET /health` — health check endpoint
- Docker support with multi-arch images
- HF Spaces deployment support
- Configurable via environment variables
