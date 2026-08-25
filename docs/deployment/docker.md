---
title: Docker
---

# Docker Deployment

## Quick start

```bash
docker run -p 7860:7860 -e VEILRENDER_API_TOKEN=your-secret oaklight/veilrender
```

## Images

VeilRender publishes multi-architecture images (amd64 + arm64) to:

- **Docker Hub**: `oaklight/veilrender`
- **GHCR**: `ghcr.io/oaklight/veilrender`

## Tags

| Tag | Size | Description |
|-----|------|-------------|
| `latest`, `0.4.0` | 1.07 GB | Full image with CloakBrowser embedded |
| `gateway` | 336 MB | Gateway-only image (no browser binary) |
| `0.2` | — | Latest patch in the 0.2.x series |

## Configuration

Pass environment variables with `-e`:

```bash
docker run -p 7860:7860 \
  -e VEILRENDER_API_TOKEN=your-secret \
  -e VEILRENDER_MAX_CONCURRENT=5 \
  -e VEILRENDER_TIMEOUT=60000 \
  oaklight/veilrender
```

See [Configuration](../configuration.md) for all available options.

## Docker Compose

```yaml
services:
  veilrender:
    image: oaklight/veilrender
    ports:
      - "7860:7860"
    environment:
      VEILRENDER_API_TOKEN: your-secret
      VEILRENDER_MAX_CONCURRENT: 5
    restart: unless-stopped
```

## Gateway Image

The `oaklight/veilrender:gateway` image (336 MB) contains VeilRender without a browser binary. Use it as a load-balancing gateway in front of dedicated browser workers.

## Full Image

The `oaklight/veilrender:latest` image (1.07 GB) ships with CloakBrowser embedded. It works as a standalone single-instance deployment—no external browser needed.

## Worker Pool with Docker Compose

Gateway + 2 Chromium workers:

```yaml
services:
  gateway:
    image: oaklight/veilrender:gateway
    ports:
      - "7860:7860"
    environment:
      VEILRENDER_API_TOKEN: your-secret
      VEILRENDER_WORKERS: cdp://worker1:9222,cdp://worker2:9222
      VEILRENDER_WORKER_MAX_CONCURRENT: 5
    restart: unless-stopped

  worker1:
    image: oaklight/veilrender:latest
    restart: unless-stopped

  worker2:
    image: oaklight/veilrender:latest
    restart: unless-stopped
```

## Mixed Worker Pool

Gateway + Chromium worker + Camoufox (Firefox) worker:

```yaml
services:
  gateway:
    image: oaklight/veilrender:gateway
    ports:
      - "7860:7860"
    environment:
      VEILRENDER_API_TOKEN: your-secret
      VEILRENDER_WORKERS: cdp://chromium:9222,playwright://camoufox:1234/ws
      VEILRENDER_WORKER_MAX_CONCURRENT: 5
    restart: unless-stopped

  chromium:
    image: oaklight/veilrender:latest
    restart: unless-stopped

  camoufox:
    build:
      context: .
      dockerfile: deploy/Dockerfile.camoufox
    restart: unless-stopped
```

See `deploy/Dockerfile.camoufox` in the repository for the Camoufox worker image.
