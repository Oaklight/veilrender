---
title: POST /screenshot
---

# POST /screenshot

Capture a screenshot of a URL using a headless Chromium browser.

## Request

```bash
curl -X POST http://localhost:7860/screenshot \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

### Request body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | The URL to screenshot |

## Response

Returns the screenshot as a PNG image (`image/png` content type).
