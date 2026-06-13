---
title: POST /render
---

# POST /render

Render a URL using a headless Chromium browser and return the page content in multiple formats.

## Request

```bash
curl -X POST http://localhost:7860/render \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Request body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | The URL to render |

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
