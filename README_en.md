# VeilRender

[![PyPI version](https://img.shields.io/pypi/v/veilrender?color=green)](https://pypi.org/project/veilrender/)
[![GitHub release](https://img.shields.io/github/v/release/Oaklight/veilrender?color=green)](https://github.com/Oaklight/veilrender/releases/latest)
[![CI](https://github.com/Oaklight/veilrender/actions/workflows/ci.yml/badge.svg)](https://github.com/Oaklight/veilrender/actions/workflows/ci.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/oaklight/veilrender)](https://hub.docker.com/r/oaklight/veilrender)
[![Docker Image](https://img.shields.io/docker/v/oaklight/veilrender?sort=semver&label=docker)](https://hub.docker.com/r/oaklight/veilrender)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![HF Spaces](https://img.shields.io/badge/%F0%9F%A4%97-Spaces-blue)](https://huggingface.co/spaces/oaklight/veilrender)

[中文](README_zh.md) | **English**

Headless browser rendering API — self-hostable on HF Spaces, Docker, or bare metal.

VeilRender accepts a URL and returns the fully rendered page content (HTML, Markdown, readability-extracted article) using a headless Chromium browser. Designed as a fallback for fetch tools that fail on JavaScript-rendered pages.

## Quick Start

### Docker

```bash
docker run -p 7860:7860 -e VEILRENDER_API_TOKEN=your-secret ghcr.io/oaklight/veilrender
```

### Local Development

```bash
pip install -e ".[dev]"
playwright install chromium
python -m veilrender
```

## API

### GET /health

Returns `{"status": "ok"}` if the service is running.

### POST /render

Render a URL and return the page content.

```bash
curl -X POST http://localhost:7860/render \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

Response:

```json
{
  "content": {
    "html": "...",
    "markdown": "...",
    "readability": "..."
  },
  "metadata": {
    "title": "Example Domain",
    "url": "https://example.com",
    "status_code": 200
  },
  "links": [{"url": "https://www.iana.org/domains/example", "text": "More information..."}]
}
```

### POST /screenshot

Capture a screenshot of a URL.

```bash
curl -X POST http://localhost:7860/screenshot \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

## Configuration

All settings are configured via environment variables with the `VEILRENDER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `VEILRENDER_API_TOKEN` | *(none)* | API token for authentication. If unset, auth is disabled. |
| `VEILRENDER_PORT` | `7860` | Server port |
| `VEILRENDER_HOST` | `0.0.0.0` | Server bind address |
| `VEILRENDER_TIMEOUT` | `30000` | Browser navigation timeout (ms) |
| `VEILRENDER_VIEWPORT_WIDTH` | `1280` | Browser viewport width |
| `VEILRENDER_VIEWPORT_HEIGHT` | `720` | Browser viewport height |
| `VEILRENDER_MAX_CONCURRENT` | `3` | Max concurrent browser contexts |

## Benchmark

Tested on HF Spaces (free tier, 2 vCPU) and a self-hosted VPS (3 vCPU, 1 GB container). **100% success rate** across all 46 requests per target.

| Test | HF Spaces | Self-hosted |
|------|-----------|-------------|
| Sequential × 5 (mixed URLs) | 8.72 s total | 11.81 s total |
| Concurrent × 10 (mixed URLs) | 1.40 – 9.37 s | 1.29 – 13.45 s |
| Rapid-fire × 20 (sequential) | 0.885 s avg | 1.029 s avg |
| Peak container memory | — | 614 MiB / 1 GB |

Full results: [BENCHMARK.md](BENCHMARK.md)

## License

MIT
