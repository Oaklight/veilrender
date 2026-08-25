---
title: GET /metrics
---

# GET /metrics

Prometheus metrics endpoint. Returns metrics in [Prometheus exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/).

No authentication required.

## Request

```bash
curl http://localhost:7860/metrics
```

## Response

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

## Metrics reference

### Server

| Metric | Type | Description |
|--------|------|-------------|
| `veilrender_uptime_seconds` | gauge | Server uptime in seconds |
| `veilrender_requests_total` | counter | Total requests by `endpoint` and `status` |

### Cache

| Metric | Type | Description |
|--------|------|-------------|
| `veilrender_cache_hits_total` | counter | Cache hits by `level` (`l1`, `l2`) |
| `veilrender_cache_misses_total` | counter | Cache misses |

### Latency

| Metric | Type | Description |
|--------|------|-------------|
| `veilrender_render_duration_seconds` | summary | Render latency with p50 and p95 quantiles |

### Workers

| Metric | Type | Description |
|--------|------|-------------|
| `veilrender_worker_healthy` | gauge | Whether the worker is healthy (1 = healthy, 0 = unhealthy) |
| `veilrender_worker_active_pages` | gauge | Number of active pages on the worker |
| `veilrender_worker_browser_pages` | gauge | Total browser pages on the worker |
