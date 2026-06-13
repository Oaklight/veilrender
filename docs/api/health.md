---
title: GET /health
---

# GET /health

健康检查端点，不需要认证。

## 请求

```bash
curl http://localhost:7860/health
```

## 响应

```json
{
  "status": "ok"
}
```

服务运行中返回 HTTP 200 和 `{"status": "ok"}`。
