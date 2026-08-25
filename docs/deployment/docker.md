---
title: Docker
---

# Docker 部署

## 快速开始

```bash
docker run -p 7860:7860 -e VEILRENDER_API_TOKEN=your-secret oaklight/veilrender
```

## 镜像

VeilRender 发布多架构镜像（amd64 + arm64），托管在：

- **Docker Hub**: `oaklight/veilrender`
- **GHCR**: `ghcr.io/oaklight/veilrender`

## 标签

| 标签 | 大小 | 说明 |
|------|------|------|
| `latest`、`0.4.0` | 1.07 GB | 完整镜像，内置 CloakBrowser |
| `gateway` | 336 MB | 仅 Gateway 镜像（不含浏览器二进制文件） |
| `0.2` | — | 0.2.x 系列最新补丁 |

## 配置

通过 `-e` 传递环境变量：

```bash
docker run -p 7860:7860 \
  -e VEILRENDER_API_TOKEN=your-secret \
  -e VEILRENDER_MAX_CONCURRENT=5 \
  -e VEILRENDER_TIMEOUT=60000 \
  oaklight/veilrender
```

详见 [配置](../configuration.md)。

## Docker Compose

```yaml
services:
  veilrender:
    image: oaklight/veilrender
    ports:
      - "7860:7860"
    environment:
      VEILRENDER_API_TOKEN: your-secret
      VEILRENDER_MAX_CONCURRENT: 5
    restart: unless-stopped
```

## Gateway 镜像

`oaklight/veilrender:gateway` 镜像（336 MB）仅包含 VeilRender，不含浏览器二进制文件。用作专用浏览器 Worker 前的负载均衡 Gateway。

## 完整镜像

`oaklight/veilrender:latest` 镜像（1.07 GB）内置 CloakBrowser。作为独立单实例部署使用，无需外部浏览器。

## 使用 Docker Compose 部署 Worker 池

Gateway + 2 个 Chromium Worker：

```yaml
services:
  gateway:
    image: oaklight/veilrender:gateway
    ports:
      - "7860:7860"
    environment:
      VEILRENDER_API_TOKEN: your-secret
      VEILRENDER_WORKERS: cdp://worker1:9222,cdp://worker2:9222
      VEILRENDER_WORKER_MAX_CONCURRENT: 5
    restart: unless-stopped

  worker1:
    image: oaklight/veilrender:latest
    restart: unless-stopped

  worker2:
    image: oaklight/veilrender:latest
    restart: unless-stopped
```

## 混合 Worker 池

Gateway + Chromium Worker + Camoufox (Firefox) Worker：

```yaml
services:
  gateway:
    image: oaklight/veilrender:gateway
    ports:
      - "7860:7860"
    environment:
      VEILRENDER_API_TOKEN: your-secret
      VEILRENDER_WORKERS: cdp://chromium:9222,playwright://camoufox:1234/ws
      VEILRENDER_WORKER_MAX_CONCURRENT: 5
    restart: unless-stopped

  chromium:
    image: oaklight/veilrender:latest
    restart: unless-stopped

  camoufox:
    build:
      context: .
      dockerfile: deploy/Dockerfile.camoufox
    restart: unless-stopped
```

Camoufox Worker 镜像参见仓库中的 `deploy/Dockerfile.camoufox`。
