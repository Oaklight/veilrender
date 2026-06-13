---
title: API 参考
---

# API 参考

VeilRender 提供简洁的 HTTP API，用于渲染网页和截图。

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | [`/render`](render.md) | 渲染 URL 并返回页面内容 |
| `POST` | [`/screenshot`](screenshot.md) | 截取 URL 页面截图 |
| `GET` | [`/health`](health.md) | 健康检查 |
| `GET` | [`/`](dashboard.md) | 统计仪表盘 |

## 认证

如果设置了 `VEILRENDER_API_TOKEN`，所有 `/render` 和 `/screenshot` 请求需要携带 Bearer token：

```
Authorization: Bearer <your-token>
```

`/health` 和 `/`（仪表盘）端点不需要认证。
