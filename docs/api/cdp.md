---
title: WS /cdp
---

# WS /cdp

Chrome DevTools Protocol (CDP) WebSocket 代理，直接连接到 VeilRender 管理的浏览器实例。允许外部工具通过 WebSocket 控制浏览器。

设置了 `VEILRENDER_API_TOKEN` 时需要认证（通过 `token` 查询参数传递）。

## 请求

```bash
# 连接到默认 Worker
websocat ws://localhost:7860/cdp?token=<your-token>

# 指定连接到池中的某个 Worker
websocat ws://localhost:7860/cdp?worker=1&token=<your-token>
```

### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `worker` | integer | *（自动）* | 按索引指定目标 Worker。省略时由 Gateway 自动选择可用 Worker。 |
| `token` | string | — | API 认证令牌（设置了 `VEILRENDER_API_TOKEN` 时必填） |

## 通过 Playwright 使用

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

## 通过 Puppeteer 使用

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

## 注意事项

- WebSocket 连接直接代理到浏览器的 CDP 端点。
- 在多 Worker 池模式下，使用 `?worker=N` 将连接固定到指定 Worker。
- 连接保持打开状态，直到客户端断开或 Worker 变为不健康。
