---
title: API Reference
---

# API Reference

VeilRender exposes an HTTP API for rendering web pages, capturing screenshots, and managing browser workers.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | [`/render`](render.md) | Render a URL and return page content |
| `POST` | [`/screenshot`](screenshot.md) | Capture a screenshot of a URL |
| `GET` | [`/health`](health.md) | Health check |
| `GET` | [`/metrics`](metrics.md) | Prometheus metrics |
| `GET` | [`/stats`](stats.md) | Dashboard stats JSON API |
| `WS` | [`/cdp`](cdp.md) | CDP WebSocket proxy |
| `GET` | [`/`](dashboard.md) | Stats dashboard |

## Authentication

If `VEILRENDER_API_TOKEN` is set, all `/render` and `/screenshot` requests require a Bearer token:

```
Authorization: Bearer <your-token>
```

The `/health`, `/metrics`, `/stats`, and `/` (dashboard) endpoints do not require authentication. The `/cdp` endpoint requires authentication if `VEILRENDER_API_TOKEN` is set.
