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
