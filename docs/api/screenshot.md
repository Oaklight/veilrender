---
title: POST /screenshot
---

# POST /screenshot

使用无头 Chromium 浏览器截取指定 URL 的页面截图。

## 请求

```bash
curl -X POST http://localhost:7860/screenshot \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

### 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 要截图的 URL |

## 响应

返回 PNG 格式的截图（`image/png` content type）。
