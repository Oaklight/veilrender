---
name: veilrender
version: 0.4.0
description: "Render JavaScript-heavy pages via VeilRender API: fetch fully rendered HTML, Markdown, readability text, or PNG screenshots from URLs that fail with plain HTTP fetch."
homepage: https://github.com/Oaklight/veilrender
metadata:
  {
    "openclaw":
      {
        "emoji": "👻",
        "requires": { "bins": ["curl"] },
      },
  }
---

# VeilRender — Headless Browser Rendering

Render JavaScript-heavy or bot-protected pages via a VeilRender API instance.
Use this when `curl`/`fetch` returns empty or incomplete content because the
page requires a real browser to render.

## Setup

Before first use, check if the user already has a VeilRender instance configured.

**Step 1**: Check for existing configuration:
```bash
echo "URL: ${VEILRENDER_URL:-not set}"
echo "Token: ${VEILRENDER_TOKEN:+configured}"
```

**Step 2**: If either is missing, **ask the user**:
- "Do you have a hosted VeilRender instance? If so, what is the URL and API token?"
- If they don't have one, suggest self-hosting:
  ```bash
  docker run -d -p 7860:7860 -e VEILRENDER_API_TOKEN=changeme oaklight/veilrender:latest
  # Then set:
  export VEILRENDER_URL="http://localhost:7860"
  export VEILRENDER_TOKEN="changeme"
  ```

**Step 3**: Verify connectivity:
```bash
curl -sf "$VEILRENDER_URL/health" | jq .
# Expected: {"status": "ok"}
```

If health check fails, do NOT proceed — ask the user to check their instance.

### Required environment

| Variable | Required | Description |
|----------|----------|-------------|
| `VEILRENDER_URL` | Yes | Base URL of the VeilRender instance |
| `VEILRENDER_TOKEN` | If auth enabled | API Bearer token |

## Render a page

Returns rendered HTML, Markdown, and/or readability-extracted article text.

```bash
curl -s -X POST "$VEILRENDER_URL/render" \
  -H "Authorization: Bearer $VEILRENDER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "formats": ["readability"]}' | jq .
```

### Request body

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | *(required)* | URL to render |
| `formats` | string[] | `["html"]` | `html`, `readability`, `markdown` |
| `wait_until` | string | `"load"` | `load`, `domcontentloaded`, `networkidle` |

### Response

```json
{
  "content": {
    "html": "<html>...",
    "readability": "Article text...",
    "markdown": "# Title\n..."
  },
  "metadata": {
    "title": "Page Title",
    "url": "https://example.com/",
    "status_code": 200
  },
  "links": [{"url": "https://...", "text": "Link text"}]
}
```

## Take a screenshot

Returns a PNG image of the rendered page.

```bash
curl -s -X POST "$VEILRENDER_URL/screenshot" \
  -H "Authorization: Bearer $VEILRENDER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' -o screenshot.png
```

### Screenshot options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | *(required)* | URL to screenshot |
| `full_page` | bool | `false` | Capture full scrollable page |
| `viewport_width` | int | `1280` | Override viewport width |
| `viewport_height` | int | `720` | Override viewport height |

## Check service health

```bash
curl -s "$VEILRENDER_URL/health" | jq .
# {"status": "ok"}
```

## Common patterns

### Render a JS-heavy page when fetch fails

```bash
# Plain fetch returns empty/broken content
curl -s https://spa-site.com  # → empty or loading spinner HTML

# Use VeilRender to get the fully rendered page
curl -s -X POST "$VEILRENDER_URL/render" \
  -H "Authorization: Bearer $VEILRENDER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://spa-site.com", "formats": ["readability"], "wait_until": "networkidle"}' \
  | jq -r '.content.readability'
```

### Extract article text for LLM consumption

```bash
curl -s -X POST "$VEILRENDER_URL/render" \
  -H "Authorization: Bearer $VEILRENDER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$URL\", \"formats\": [\"readability\"]}" \
  | jq -r '.content.readability'
```

### Batch render multiple URLs

```bash
for url in "https://site1.com" "https://site2.com" "https://site3.com"; do
  echo "=== $url ==="
  curl -s -X POST "$VEILRENDER_URL/render" \
    -H "Authorization: Bearer $VEILRENDER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$url\", \"formats\": [\"readability\"]}" \
    | jq -r '.metadata.title + ": " + (.content.readability | length | tostring) + " chars"'
done
```

## Error handling

| HTTP Code | Meaning |
|-----------|---------|
| 200 | Success |
| 401 | Invalid or missing API token |
| 422 | Invalid request (bad URL, missing fields) |
| 502 | Browser rendering failed (timeout, crash, blocked URL) |

On 502, check if the URL is accessible and try with `"wait_until": "networkidle"` for slow-loading pages.

## Notes

- VeilRender uses a stealth browser (CloakBrowser) — it passes bot detection on most sites
- Pages with CAPTCHAs may still fail; consider adding a residential proxy
- The service blocks ad/tracker domains by default (`VEILRENDER_RESOURCE_FILTER=true`)
- Stats dashboard available at `$VEILRENDER_URL/` (no auth needed for the dashboard)
