# VeilRender

[![PyPI version](https://img.shields.io/pypi/v/veilrender?color=green)](https://pypi.org/project/veilrender/)
[![GitHub release](https://img.shields.io/github/v/release/Oaklight/veilrender?color=green)](https://github.com/Oaklight/veilrender/releases/latest)
[![CI](https://github.com/Oaklight/veilrender/actions/workflows/ci.yml/badge.svg)](https://github.com/Oaklight/veilrender/actions/workflows/ci.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/oaklight/veilrender?color=blue)](https://hub.docker.com/r/oaklight/veilrender)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**中文** | [English](README_en.md)

具备反检测能力的无头浏览器渲染 API —— 支持通过 Docker 或 pip 自托管部署。

VeilRender 接受一个 URL，使用反检测 Chromium 浏览器返回完整渲染后的页面内容（HTML、Markdown、readability 提取的正文）。专为 fetch 工具在遇到 JavaScript 渲染页面或反爬页面时失败的场景而设计。

## 特性

- **反检测渲染** —— [CloakBrowser](https://github.com/CloakHQ/CloakBrowser)（71 项 C++ 指纹补丁）+ [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python)（Playwright 反检测分支）
- **多种输出格式** —— 原始 HTML、Markdown、readability 提取的正文
- **截图功能** —— 全页或视口 PNG 截图
- **水平扩展** —— 网关 + 远程浏览器工作节点池，支持健康检查和自动重连
- **混合浏览器后端** —— Chromium（CDP）和 Firefox/Camoufox（Playwright 协议）可在同一池中共存
- **Prometheus 指标** —— `/metrics` 端点提供延迟百分位、每工作节点状态指标
- **仪表盘** —— `/` 路径展示实时统计，支持国际化（en/zh），含 SVG 容量仪表
- **广告/追踪器拦截** —— 来自 [StevenBlack/hosts](https://github.com/StevenBlack/hosts) 的 82k 域名黑名单
- **渲染缓存** —— L1 内存缓存 + L2 S3 兼容存储（R2、Oracle、AWS）
- **CDP 代理** —— 通过 `/cdp` 直接 WebSocket 访问浏览器
- **零外部依赖**（除 `patchright` 外）—— HTTP 服务器、S3 客户端、HTML 解析均为内置模块

## 快速开始

### Docker（推荐）

```bash
# 单实例模式，内置 CloakBrowser
docker run -p 7860:7860 -e VEILRENDER_API_TOKEN=your-secret oaklight/veilrender:latest

# 仅网关模式（不含浏览器，336MB）
docker run -p 7860:7860 oaklight/veilrender:gateway
```

### pip

```bash
pip install veilrender
veilrender  # 在 :7860 启动，首次运行时自动下载 CloakBrowser 二进制文件
```

### Docker Compose —— 工作节点池

```yaml
# docker-compose.yaml
services:
  veilrender:
    image: oaklight/veilrender:gateway
    ports: ["7860:7860"]
    environment:
      - VEILRENDER_WORKERS=cdp://browser-worker:9222
  browser-worker:
    image: cloakhq/cloakbrowser
    command: ["cloakserve"]
```

更多 compose 示例（包括 Chromium + Camoufox 混合池）请参阅 `deploy/` 目录。

## API

### GET /health

```json
{"status": "ok"}
```

### POST /render

渲染 URL 并返回页面内容。

```bash
curl -X POST http://localhost:7860/render \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "formats": ["html", "readability", "markdown"]}'
```

请求体：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | string | *（必填）* | 要渲染的 URL |
| `formats` | string[] | `["html"]` | 输出格式：`html`、`readability`、`markdown` |
| `wait_until` | string | `"load"` | Playwright 等待策略：`load`、`domcontentloaded`、`networkidle` |

### POST /screenshot

捕获 PNG 截图。

```bash
curl -X POST http://localhost:7860/screenshot \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' -o screenshot.png
```

### GET /metrics

Prometheus 格式的指标输出，包括运行时间、请求计数器、缓存统计、延迟摘要（p50/p95）以及每工作节点的健康状态指标。

### GET /stats

仪表盘实时数据的 JSON API（由仪表盘 UI 轮询获取）。

### WS /cdp

直接连接浏览器的 CDP WebSocket 代理。支持 `?worker=N` 参数指定池中的特定工作节点。

## 配置

所有设置通过 `VEILRENDER_*` 环境变量配置：

### 核心配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VEILRENDER_API_TOKEN` | *（无）* | Bearer 认证令牌。未设置时禁用认证 |
| `VEILRENDER_PORT` | `7860` | 服务端口 |
| `VEILRENDER_HOST` | `0.0.0.0` | 绑定地址 |
| `VEILRENDER_TIMEOUT` | `30000` | 页面加载超时时间（毫秒） |
| `VEILRENDER_VIEWPORT_WIDTH` | `1280` | 浏览器视口宽度 |
| `VEILRENDER_VIEWPORT_HEIGHT` | `720` | 浏览器视口高度 |
| `VEILRENDER_MAX_CONCURRENT` | `5` | 最大并发页面数（单实例模式） |

### 工作节点池

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VEILRENDER_WORKERS` | *（无）* | 逗号分隔的工作节点端点（启用池模式） |
| `VEILRENDER_WORKER_MAX_CONCURRENT` | `5` | 每工作节点的页面并发数 |
| `VEILRENDER_WORKER_HEALTH_INTERVAL` | `10` | 健康检查间隔（秒） |

工作节点端点格式：
- `cdp://host:9222` 或 `http://host:9222` —— Chromium CDP 工作节点
- `playwright://host:1234/ws-path` —— Firefox/Camoufox Playwright 工作节点
- `playwrights://host:1234/ws-path` —— TLS Playwright 工作节点

### 浏览器二进制文件

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLOAKBROWSER_BINARY` | *（自动）* | 自定义浏览器二进制文件路径 |
| `CLOAKBROWSER_MIRROR` | *（无）* | GitHub 镜像 URL，适用于中国大陆网络环境（如 `https://ghfast.top`） |

二进制文件检测顺序：环境变量 → `~/.cloakbrowser/*/chrome` → 从 GitHub Releases 自动下载。

### 缓存与存储

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VEILRENDER_CACHE_ENABLED` | `false` | 启用渲染缓存 |
| `VEILRENDER_CACHE_TTL` | `86400` | 缓存 TTL（秒） |
| `VEILRENDER_RESOURCE_FILTER` | `true` | 渲染时拦截广告/追踪器 |
| `VEILRENDER_S3_ENDPOINT` | *（无）* | L2 缓存的 S3 端点 |
| `VEILRENDER_S3_ACCESS_KEY` | *（无）* | S3 访问密钥 |
| `VEILRENDER_S3_SECRET_KEY` | *（无）* | S3 密钥 |

## 部署模式

### 单实例模式（完整镜像，1.07GB）

内置 CloakBrowser —— 最简单的部署方式，无外部依赖。

```bash
docker run -p 7860:7860 -e VEILRENDER_API_TOKEN=secret oaklight/veilrender:latest
```

### 网关 + 工作节点池（网关镜像，336MB）

浏览器容器独立扩展。网关通过最少连接数策略路由请求。

```yaml
services:
  veilrender:
    image: oaklight/veilrender:gateway
    environment:
      - VEILRENDER_WORKERS=cdp://worker1:9222,cdp://worker2:9222

  worker1:
    image: cloakhq/cloakbrowser
    command: ["cloakserve"]

  worker2:
    image: cloakhq/cloakbrowser
    command: ["cloakserve"]
```

### 混合池（Chromium + Camoufox）

双引擎反检测：CloakBrowser 应对 Chromium 指纹检测站点，Camoufox 应对 Firefox 指纹检测站点。

```yaml
services:
  veilrender:
    image: oaklight/veilrender:gateway
    environment:
      - VEILRENDER_WORKERS=cdp://chromium:9222,playwright://camoufox:1234/ws

  chromium:
    image: cloakhq/cloakbrowser
    command: ["cloakserve"]

  camoufox:
    build: deploy/Dockerfile.camoufox
```

## Docker 镜像

| 标签 | 大小 | 内容 |
|------|------|------|
| `latest` / `0.4.0` | 1.07GB | 完整版 —— Patchright + CloakBrowser |
| `gateway` | 336MB | 仅网关 —— 不含浏览器二进制文件 |

本地构建：
```bash
make build          # 完整镜像
make build-gateway  # 网关镜像
```

## 开发

```bash
# 环境搭建
pip install -e ".[dev]"

# 本地运行
make dev            # 在 :7860 启动

# 代码检查与类型检查
make lint           # ruff check --fix && ruff format
make typecheck      # ty check

# 开发环境部署
make deploy-dev SSH_TARGET=oaklight.buttercup
```

## 许可证

MIT
