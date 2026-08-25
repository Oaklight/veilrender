---
title: GET /stats
---

# GET /stats

JSON API for live dashboard data. This endpoint is polled by the built-in dashboard UI.

No authentication required.

## Request

```bash
curl http://localhost:7860/stats
```

## Response

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

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| `uptime` | number | Server uptime in seconds |
| `total_requests` | integer | Total requests served since startup |
| `active_requests` | integer | Currently in-flight requests |
| `cache.l1_hits` | integer | L1 (in-memory) cache hits |
| `cache.l2_hits` | integer | L2 (S3-compatible) cache hits |
| `cache.misses` | integer | Cache misses |
| `workers` | array | Per-worker status |
| `workers[].id` | integer | Worker index |
| `workers[].healthy` | boolean | Whether the worker is reachable |
| `workers[].active_pages` | integer | Pages currently rendering |
| `workers[].browser_pages` | integer | Total browser pages allocated |
| `workers[].backend` | string | Browser backend (`chromium`, `camoufox`) |
| `latency.p50` | number | Median render latency in seconds |
| `latency.p95` | number | 95th percentile render latency in seconds |
