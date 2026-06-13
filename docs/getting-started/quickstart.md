---
title: 快速开始
---

# 快速开始

## 启动服务

### 使用 Docker（推荐）

```bash
docker run -p 7860:7860 -e VEILRENDER_API_TOKEN=your-secret oaklight/veilrender
```

### 使用 pip

```bash
python -m veilrender
```

服务默认启动在 `http://localhost:7860`。

## 发送第一个请求

### 渲染页面

```bash
curl -X POST http://localhost:7860/render \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

响应：

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

### 页面截图

```bash
curl -X POST http://localhost:7860/screenshot \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

### 健康检查

```bash
curl http://localhost:7860/health
```

服务运行中返回 `{"status": "ok"}`。

## 试用公开演示

无需认证：

```bash
curl -X POST https://oaklight-veilrender-public.hf.space/render \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```
