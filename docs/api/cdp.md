---
title: WS /cdp
---

# WS /cdp

Direct Chrome DevTools Protocol (CDP) WebSocket proxy to the browser. Allows external tools to connect to a browser instance managed by VeilRender.

Requires authentication if `VEILRENDER_API_TOKEN` is set (passed via the `token` query parameter).

## Request

```bash
# Connect to default worker
websocat ws://localhost:7860/cdp?token=<your-token>

# Target a specific worker in the pool
websocat ws://localhost:7860/cdp?worker=1&token=<your-token>
```

### Query parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `worker` | integer | *(auto)* | Target a specific worker by index. If omitted, the gateway selects an available worker. |
| `token` | string | — | API token for authentication (required if `VEILRENDER_API_TOKEN` is set) |

## Usage with Playwright

```python
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(
            "ws://localhost:7860/cdp?token=<your-token>"
        )
        page = await browser.new_page()
        await page.goto("https://example.com")
        print(await page.title())
        await browser.close()

asyncio.run(main())
```

## Usage with Puppeteer

```javascript
const puppeteer = require("puppeteer-core");

(async () => {
  const browser = await puppeteer.connect({
    browserWSEndpoint: "ws://localhost:7860/cdp?token=<your-token>",
  });
  const page = await browser.newPage();
  await page.goto("https://example.com");
  console.log(await page.title());
  await browser.close();
})();
```

## Notes

- The WebSocket connection is proxied directly to the browser's CDP endpoint.
- In a multi-worker pool, use `?worker=N` to pin the connection to a specific worker.
- The connection stays open until the client disconnects or the worker becomes unhealthy.
