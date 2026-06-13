---
title: Quick Start
---

# Quick Start

## Start the server

### With Docker (recommended)

```bash
docker run -p 7860:7860 -e VEILRENDER_API_TOKEN=your-secret oaklight/veilrender
```

### With pip

```bash
python -m veilrender
```

The server starts on `http://localhost:7860` by default.

## Make your first request

### Render a page

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
  "links": [
    {
      "url": "https://www.iana.org/domains/example",
      "text": "More information..."
    }
  ]
}
```

### Take a screenshot

```bash
curl -X POST http://localhost:7860/screenshot \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

### Check health

```bash
curl http://localhost:7860/health
```

Returns `{"status": "ok"}` if the service is running.

## Try the public demo

No authentication required:

```bash
curl -X POST https://oaklight-veilrender-public.hf.space/render \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```
