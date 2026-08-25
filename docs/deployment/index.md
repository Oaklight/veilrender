---
title: 部署
---

# 部署

VeilRender 支持两种部署模式：

- **单实例** — 使用完整镜像（`oaklight/veilrender:latest`），内置 CloakBrowser。最简单的方式，适合中等负载。
- **Gateway + Worker 池** — 使用 Gateway 镜像（`oaklight/veilrender:gateway`）配合专用浏览器 Worker，实现水平扩展和混合浏览器引擎。

部署方式：

- **[Docker](docker.md)** — 推荐用于生产环境
- **[HF Spaces](hf-spaces.md)** — 使用 Hugging Face 免费托管
- **[物理机部署](bare-metal.md)** — 直接安装在服务器上
