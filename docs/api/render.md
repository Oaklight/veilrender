---
title: POST /render
---

# POST /render

Render a URL using a stealth headless browser and return the page content in multiple formats.

## Request

```bash
curl -X POST http://localhost:7860/render \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "formats": ["html", "markdown"], "wait_until": "networkidle"}'
```

### Request body

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | *(required)* | URL to render |
| `formats` | string[] | `["html"]` | Output formats: `html`, `readability`, `markdown` |
| `wait_until` | string | `"load"` | Playwright wait strategy: `load`, `domcontentloaded`, `networkidle` |

## Response

```json
{
  "content": {
    "html": "<!doctype html>...",
    "markdown": "# Example Domain\n...",
    "readability": "Example Domain\n..."
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

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| `content.html` | string | Full rendered HTML of the page |
| `content.markdown` | string | Page content converted to Markdown |
| `content.readability` | string | Readability-extracted article text |
| `metadata.title` | string | Page title |
| `metadata.url` | string | Final URL (after redirects) |
| `metadata.status_code` | integer | HTTP status code |
| `links` | array | Links found on the page |
