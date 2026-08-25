---
title: GET /stats
---

# GET /stats

仪表盘实时数据的 JSON API。此端点由内置仪表盘 UI 轮询调用。

无需认证。

## 请求

```bash
curl http://localhost:7860/stats
```

## 响应

```json
{
  "uptime": 3621.42,
  "total_requests": 192,
  "active_requests": 2,
  "cache": {
    "l1_hits": 89,
    "l2_hits": 23,
    "misses": 35
  },
  "workers": [
    {
      "id": 0,
      "healthy": true,
      "active_pages": 2,
      "browser_pages": 5,
      "backend": "chromium"
    },
    {
      "id": 1,
      "healthy": true,
      "active_pages": 0,
      "browser_pages": 5,
      "backend": "camoufox"
    }
  ],
  "latency": {
    "p50": 1.23,
    "p95": 4.87
  }
}
```

### 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `uptime` | number | 服务器运行时间（秒） |
| `total_requests` | integer | 启动以来的总请求数 |
| `active_requests` | integer | 当前进行中的请求数 |
| `cache.l1_hits` | integer | L1（内存）缓存命中数 |
| `cache.l2_hits` | integer | L2（S3 兼容存储）缓存命中数 |
| `cache.misses` | integer | 缓存未命中数 |
| `workers` | array | 各 Worker 状态 |
| `workers[].id` | integer | Worker 索引 |
| `workers[].healthy` | boolean | Worker 是否可达 |
| `workers[].active_pages` | integer | 正在渲染的页面数 |
| `workers[].browser_pages` | integer | 已分配的浏览器页面总数 |
| `workers[].backend` | string | 浏览器后端（`chromium`、`camoufox`） |
| `latency.p50` | number | 渲染延迟中位数（秒） |
| `latency.p95` | number | 渲染延迟 95 分位数（秒） |
