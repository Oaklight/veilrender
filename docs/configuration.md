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

## Worker 池

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VEILRENDER_WORKERS` | *(无)* | 逗号分隔的 Worker 端点列表（启用池模式） |
| `VEILRENDER_WORKER_MAX_CONCURRENT` | `5` | 每个 Worker 的页面并发数 |
| `VEILRENDER_WORKER_HEALTH_INTERVAL` | `10` | 健康检查间隔（秒） |

设置 `VEILRENDER_WORKERS` 后，VeilRender 以 Gateway 模式运行，将渲染请求分发到各 Worker。Worker 端点格式：

- `cdp://host:9222` 或 `http://host:9222` — Chromium CDP Worker
- `playwright://host:1234/ws-path` — Firefox/Camoufox Playwright Worker
- `playwrights://host:1234/ws-path` — TLS Playwright Worker

## 浏览器二进制文件

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLOAKBROWSER_BINARY` | *（自动）* | 自定义浏览器二进制文件路径 |
| `CLOAKBROWSER_MIRROR` | *(无)* | GitHub 镜像 URL，适用于国内加速（如 `https://ghfast.top`） |

二进制文件检测顺序：环境变量 → `~/.cloakbrowser/*/chrome` → 从 GitHub Releases 自动下载。

## 缓存与存储

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VEILRENDER_CACHE_ENABLED` | `false` | 启用渲染缓存 |
| `VEILRENDER_CACHE_TTL` | `86400` | 缓存 TTL（秒） |
| `VEILRENDER_RESOURCE_FILTER` | `true` | 渲染时拦截广告/追踪器 |
| `VEILRENDER_S3_ENDPOINT` | *(无)* | L2 缓存的 S3 端点 |
| `VEILRENDER_S3_ACCESS_KEY` | *(无)* | S3 访问密钥 |
| `VEILRENDER_S3_SECRET_KEY` | *(无)* | S3 私密密钥 |
