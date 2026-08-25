---
title: 更新日志
---

# 更新日志

VeilRender 的所有重要变更记录在此。格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)。

## [0.4.0] — 2026-08-24

### 新增

- **远程浏览器 Worker 池**，支持水平扩展 — `VEILRENDER_WORKERS` 环境变量通过最少连接路由将请求分发到远程 CDP 端点
- **Firefox/Camoufox Worker 支持** — `playwright://` 协议前缀，可在 CDP Worker 旁连接 Playwright 兼容浏览器
- `LocalWorker` / `RemoteWorker` / `PlaywrightWorker` 抽象，共享 `_BaseWorker` 接口
- Worker 健康检查与远程 Worker 自动重连
- CDP 代理 `?worker=N` 查询参数，支持定向 Worker 路由
- 每 Worker 的 Prometheus 指标：`veilrender_worker_healthy`、`veilrender_worker_active_pages`、`veilrender_worker_browser_pages`
- 通过 CDP `/json` 端点获取真实浏览器页面数，实现精确容量报告
- Prometheus 指标端点 `GET /metrics` — 零依赖文本格式，包含运行时间、浏览器状态、活跃页面数、请求计数器、缓存查询和延迟摘要（p50/p95）
- 仪表盘国际化：语言选择下拉菜单（en/zh），使用 localStorage 持久化
- 仪表盘 `GET /stats` JSON API，用于实时数据轮询
- 仪表盘 SVG 环形仪表盘，可视化容量使用
- 多目标 Dockerfile：`gateway`（336 MB，不含浏览器）和 `full`（1.07 GB，内置 CloakBrowser）
- Compose 文件：`deploy/compose.yaml`（单实例）、`deploy/compose-pool.yaml`（Chromium 池）、`deploy/compose-pool-mixed.yaml`（Chromium + Camoufox 混合池）
- `deploy/Dockerfile.camoufox` 用于 Camoufox 服务 Worker 镜像
- `CLOAKBROWSER_MIRROR` 环境变量，适用于国内下载加速（如 `https://ghfast.top`）
- `CLOAKBROWSER_BINARY` 环境变量，支持自定义浏览器二进制文件路径
- 从 GitHub Releases 自动下载 CloakBrowser 二进制文件，无需 pip 包

### 变更

- **从 Playwright 迁移到 Patchright** — 直接替换，附带 Chromium 隐身驱动补丁
- **用内置零依赖 `S3Client` 替换 `minio`** — 仅 `patchright` 作为运行时依赖
- 移除 `cloakbrowser` pip 依赖 — 二进制文件改为直接从 GitHub Releases 下载
- Docker 镜像大小：完整版 1.43 GB → 1.07 GB，Gateway 498 MB → 336 MB
- 仪表盘重新设计：深色主题 — 纯黑背景、薄荷绿点缀、DM Sans + JetBrains Mono 字体
- 仪表盘数据刷新：基于 fetch 的轮询替代整页刷新（不再闪烁或滚动位置重置）

### 移除

- HF Spaces 公开演示徽章（Space 已下线）
- `cloakbrowser` pip 依赖（改为自动下载二进制文件）
- `minio` pip 依赖（被内置 S3Client 替代）

## [0.3.1] — 2026-07-04

### 新增

- URL 校验：仅允许 `http://` 和 `https://` 协议；拦截 `file://`、`data:`、`javascript:`
- DNS 解析与私有 IP 拦截：拒绝回环地址、RFC1918 地址、链路本地地址、云元数据端点（169.254.x.x）— 防止 SSRF
- 类 fail2ban 的 IP 频率限制：5 分钟内 3 次认证失败 → 封禁 10 分钟，支持 `X-Forwarded-For`

### 变更

- `max_body_size` 从 10 MB 降至 64 KB

### 修复

- **严重**：通过 `file:///etc/passwd` 的 SSRF — Playwright `page.goto()` 接受任意协议
- **严重**：通过 `http://127.0.0.1:9222` 的 SSRF — CDP 调试端点暴露 WebSocket URL，可导致远程代码执行
- **严重**：无 URL 校验 — 用户提供的 URL 未经过滤直接传递给 Playwright
- **中等**：接受 `data:` URL — 攻击者可渲染任意 HTML 内容

## [0.3.0] — 2026-06-26

### 新增

- 使用 [StevenBlack/hosts](https://github.com/StevenBlack/hosts) 社区黑名单（约 82k 广告/追踪/恶意域名）的出站请求过滤，通过 Playwright `page.route()` 拦截
- 两级渲染缓存：L1 内存 `TTLCache` + L2 S3 兼容持久化存储 — 支持 Cloudflare R2、Oracle Object Storage、AWS S3 等
- L2 TTL 通过嵌入的 `_stored_at` 时间戳在读取时校验
- 启动时自动设置 S3 生命周期规则（7× TTL 过期，作为批量清理安全网）
- 新增环境变量：`VEILRENDER_RESOURCE_FILTER`、`VEILRENDER_CACHE_ENABLED`、`VEILRENDER_CACHE_TTL`、`VEILRENDER_S3_ENDPOINT` 等

## [0.2.0] — 2026-06-13

### 新增

- `GET /` 统计仪表盘，包含徽章、容量条和响应式布局
- 公开 HF Space（无需认证）和在线演示徽章

### 变更

- 默认 `max_concurrent` 从 3 提升到 5
- 以运行时用户预下载 Chromium，避免启动时重复下载

## [0.1.0] — 2026-06-12

### 新增

- 核心渲染 API：`POST /render`、`POST /screenshot`、`GET /health`
- CDP WebSocket 代理 `/cdp`，直接控制浏览器
- 基于 `Authorization: Bearer` 头的 Token 认证
- 请求级浏览器上下文隔离，支持可配置并发数
- [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) 集成 — 带指纹补丁的隐身 Chromium
- 13 个内置 [zerodep](https://github.com/Oaklight/zerodep) 模块 — 最少外部依赖
- Docker 镜像，支持多架构（amd64/arm64）
- GitHub CI 流水线：pre-commit、Docker 构建、自动部署
- 标签推送时发布到 PyPI
- 双语 README（中/英）

[0.4.0]: https://github.com/Oaklight/veilrender/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/Oaklight/veilrender/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Oaklight/veilrender/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Oaklight/veilrender/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Oaklight/veilrender/releases/tag/v0.1.0
