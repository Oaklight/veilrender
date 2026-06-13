---
title: 配置
---

# 配置

所有设置通过 `VEILRENDER_` 前缀的环境变量配置。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VEILRENDER_API_TOKEN` | *(无)* | API 认证令牌。未设置时认证关闭。 |
| `VEILRENDER_PORT` | `7860` | 服务端口 |
| `VEILRENDER_HOST` | `0.0.0.0` | 服务绑定地址 |
| `VEILRENDER_TIMEOUT` | `30000` | 浏览器导航超时（毫秒） |
| `VEILRENDER_VIEWPORT_WIDTH` | `1280` | 浏览器视口宽度（像素） |
| `VEILRENDER_VIEWPORT_HEIGHT` | `720` | 浏览器视口高度（像素） |
| `VEILRENDER_MAX_CONCURRENT` | `5` | 最大并发浏览器上下文数 |

## 认证

设置 `VEILRENDER_API_TOKEN` 后，所有 `/render` 和 `/screenshot` 请求必须携带 Bearer token：

```
Authorization: Bearer <your-token>
```

未设置时认证关闭，所有端点公开访问。

## 并发

`VEILRENDER_MAX_CONCURRENT` 控制同时渲染的页面数量。值越大内存占用越高。在 1 GB 容器上，3–5 个并发上下文效果较好。仪表盘 `/` 可查看当前容量使用情况。
