---
title: API Reference
---

# API Reference

VeilRender exposes a simple HTTP API for rendering web pages and capturing screenshots.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | [`/render`](render.md) | Render a URL and return page content |
| `POST` | [`/screenshot`](screenshot.md) | Capture a screenshot of a URL |
| `GET` | [`/health`](health.md) | Health check |
| `GET` | [`/`](dashboard.md) | Stats dashboard |

## Authentication

If `VEILRENDER_API_TOKEN` is set, all `/render` and `/screenshot` requests require a Bearer token:

```
Authorization: Bearer <your-token>
```

The `/health` and `/` (dashboard) endpoints do not require authentication.
