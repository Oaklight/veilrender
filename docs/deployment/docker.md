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

| 标签 | 说明 |
|------|------|
| `latest` | 最新版本 |
| `0.2` | 0.2.x 系列最新补丁 |
| `0.2.0` | 指定版本 |

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
