---
title: POST /render
---

# POST /render

使用无头 Chromium 浏览器渲染指定 URL，并以多种格式返回页面内容。

## 请求

```bash
curl -X POST http://localhost:7860/render \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### 请求体

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 要渲染的 URL |

## 响应

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

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `content.html` | string | 完整渲染后的页面 HTML |
| `content.markdown` | string | 页面内容转换为 Markdown |
| `content.readability` | string | readability 提取的文章文本 |
| `metadata.title` | string | 页面标题 |
| `metadata.url` | string | 最终 URL（重定向后） |
| `metadata.status_code` | integer | HTTP 状态码 |
| `links` | array | 页面中的链接 |
