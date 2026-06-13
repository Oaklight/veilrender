---
title: 安装
---

# 安装

VeilRender 可以通过 pip 安装或以 Docker 容器运行。

## 通过 pip 安装

```bash
pip install veilrender
```

VeilRender 底层使用 [CloakBrowser](https://github.com/Oaklight/cloakbrowser)，需要 Chromium。安装方法：

```bash
playwright install chromium
```

## 通过 Docker 安装

从 Docker Hub 拉取官方镜像：

```bash
docker pull oaklight/veilrender
```

或从 GitHub Container Registry 拉取：

```bash
docker pull ghcr.io/oaklight/veilrender
```

## 开发模式

克隆仓库并以开发模式安装：

```bash
git clone https://github.com/Oaklight/veilrender.git
cd veilrender
pip install -e ".[dev]"
playwright install chromium
```
