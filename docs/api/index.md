---
title: API 参考
---

# API 参考

VeilRender 提供 HTTP API，用于渲染网页、截图和管理浏览器 Worker。

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | [`/render`](render.md) | 渲染 URL 并返回页面内容 |
| `POST` | [`/screenshot`](screenshot.md) | 截取 URL 页面截图 |
| `GET` | [`/health`](health.md) | 健康检查 |
| `GET` | [`/metrics`](metrics.md) | Prometheus 指标 |
| `GET` | [`/stats`](stats.md) | 仪表盘统计数据 JSON API |
| `WS` | [`/cdp`](cdp.md) | CDP WebSocket 代理 |
| `GET` | [`/`](dashboard.md) | 统计仪表盘 |

## 认证

如果设置了 `VEILRENDER_API_TOKEN`，所有 `/render` 和 `/screenshot` 请求需要携带 Bearer token：

```
Authorization: Bearer <your-token>
```

`/health`、`/metrics`、`/stats` 和 `/`（仪表盘）端点不需要认证。`/cdp` 端点在设置了 `VEILRENDER_API_TOKEN` 时需要认证。
