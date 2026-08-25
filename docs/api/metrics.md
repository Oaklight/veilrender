---
title: GET /metrics
---

# GET /metrics

Prometheus 指标端点。以 [Prometheus 文本格式](https://prometheus.io/docs/instrumenting/exposition_formats/) 返回指标数据。

无需认证。

## 请求

```bash
curl http://localhost:7860/metrics
```

## 响应

```
# HELP veilrender_uptime_seconds Server uptime in seconds
# TYPE veilrender_uptime_seconds gauge
veilrender_uptime_seconds 3621.42

# HELP veilrender_requests_total Total requests by endpoint and status
# TYPE veilrender_requests_total counter
veilrender_requests_total{endpoint="/render",status="200"} 147
veilrender_requests_total{endpoint="/render",status="500"} 3
veilrender_requests_total{endpoint="/screenshot",status="200"} 42

# HELP veilrender_cache_hits_total Cache hits by level
# TYPE veilrender_cache_hits_total counter
veilrender_cache_hits_total{level="l1"} 89
veilrender_cache_hits_total{level="l2"} 23

# HELP veilrender_cache_misses_total Cache misses
# TYPE veilrender_cache_misses_total counter
veilrender_cache_misses_total 35

# HELP veilrender_render_duration_seconds Render request latency
# TYPE veilrender_render_duration_seconds summary
veilrender_render_duration_seconds{quantile="0.5"} 1.23
veilrender_render_duration_seconds{quantile="0.95"} 4.87
veilrender_render_duration_seconds_sum 312.5
veilrender_render_duration_seconds_count 147

# HELP veilrender_worker_healthy Whether the worker is healthy (1 = healthy, 0 = unhealthy)
# TYPE veilrender_worker_healthy gauge
veilrender_worker_healthy{worker="0"} 1
veilrender_worker_healthy{worker="1"} 1

# HELP veilrender_worker_active_pages Number of active pages on the worker
# TYPE veilrender_worker_active_pages gauge
veilrender_worker_active_pages{worker="0"} 2
veilrender_worker_active_pages{worker="1"} 0

# HELP veilrender_worker_browser_pages Total browser pages on the worker
# TYPE veilrender_worker_browser_pages gauge
veilrender_worker_browser_pages{worker="0"} 5
veilrender_worker_browser_pages{worker="1"} 5
```

## 指标参考

### 服务器

| 指标 | 类型 | 说明 |
|------|------|------|
| `veilrender_uptime_seconds` | gauge | 服务器运行时间（秒） |
| `veilrender_requests_total` | counter | 按 `endpoint` 和 `status` 分类的总请求数 |

### 缓存

| 指标 | 类型 | 说明 |
|------|------|------|
| `veilrender_cache_hits_total` | counter | 按 `level`（`l1`、`l2`）分类的缓存命中数 |
| `veilrender_cache_misses_total` | counter | 缓存未命中数 |

### 延迟

| 指标 | 类型 | 说明 |
|------|------|------|
| `veilrender_render_duration_seconds` | summary | 渲染延迟，包含 p50 和 p95 分位数 |

### Worker

| 指标 | 类型 | 说明 |
|------|------|------|
| `veilrender_worker_healthy` | gauge | Worker 是否健康（1 = 健康，0 = 不健康） |
| `veilrender_worker_active_pages` | gauge | Worker 上正在渲染的页面数 |
| `veilrender_worker_browser_pages` | gauge | Worker 上的浏览器页面总数 |
