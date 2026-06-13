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

| Tag | Description |
|-----|-------------|
| `latest` | Latest release |
| `0.2` | Latest patch in the 0.2.x series |
| `0.2.0` | Specific version |

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
