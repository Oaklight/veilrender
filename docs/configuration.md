---
title: Configuration
---

# Configuration

All settings are configured via environment variables with the `VEILRENDER_` prefix.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VEILRENDER_API_TOKEN` | *(none)* | API token for authentication. If unset, auth is disabled. |
| `VEILRENDER_PORT` | `7860` | Server port |
| `VEILRENDER_HOST` | `0.0.0.0` | Server bind address |
| `VEILRENDER_TIMEOUT` | `30000` | Browser navigation timeout in milliseconds |
| `VEILRENDER_VIEWPORT_WIDTH` | `1280` | Browser viewport width in pixels |
| `VEILRENDER_VIEWPORT_HEIGHT` | `720` | Browser viewport height in pixels |
| `VEILRENDER_MAX_CONCURRENT` | `5` | Maximum number of concurrent browser contexts |

## Authentication

When `VEILRENDER_API_TOKEN` is set, all `/render` and `/screenshot` requests must include a Bearer token:

```
Authorization: Bearer <your-token>
```

When unset, authentication is disabled and all endpoints are publicly accessible.

## Concurrency

`VEILRENDER_MAX_CONCURRENT` controls how many pages can be rendered simultaneously. Higher values use more memory. On a 1 GB container, 3–5 concurrent contexts work well. The dashboard at `/` shows the current capacity usage.

## Worker Pool

| Variable | Default | Description |
|----------|---------|-------------|
| `VEILRENDER_WORKERS` | *(none)* | Comma-separated worker endpoints (enables pool mode) |
| `VEILRENDER_WORKER_MAX_CONCURRENT` | `5` | Per-worker page concurrency |
| `VEILRENDER_WORKER_HEALTH_INTERVAL` | `10` | Health check interval (seconds) |

When `VEILRENDER_WORKERS` is set, VeilRender runs as a gateway and distributes render requests across the listed workers. Worker endpoint formats:

- `cdp://host:9222` or `http://host:9222` — Chromium CDP worker
- `playwright://host:1234/ws-path` — Firefox/Camoufox Playwright worker
- `playwrights://host:1234/ws-path` — TLS Playwright worker

## Browser Binary

| Variable | Default | Description |
|----------|---------|-------------|
| `CLOAKBROWSER_BINARY` | *(auto)* | Path to custom browser binary |
| `CLOAKBROWSER_MIRROR` | *(none)* | GitHub mirror URL for China (e.g. `https://ghfast.top`) |

Binary detection cascade: env var → `~/.cloakbrowser/*/chrome` → auto-download from GitHub Releases.

## Cache & Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `VEILRENDER_CACHE_ENABLED` | `false` | Enable render caching |
| `VEILRENDER_CACHE_TTL` | `86400` | Cache TTL in seconds |
| `VEILRENDER_RESOURCE_FILTER` | `true` | Block ads/trackers during rendering |
| `VEILRENDER_S3_ENDPOINT` | *(none)* | S3 endpoint for L2 cache |
| `VEILRENDER_S3_ACCESS_KEY` | *(none)* | S3 access key |
| `VEILRENDER_S3_SECRET_KEY` | *(none)* | S3 secret key |
