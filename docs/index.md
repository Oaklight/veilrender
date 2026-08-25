---
title: 首页
hide:
  - navigation
---

<div style="display: flex; align-items: center; gap: 1.5em; margin-bottom: 0.5em;">
  <div>
    <h1 style="margin: 0 0 0.2em 0;">VeilRender</h1>
    <p style="margin: 0; font-size: 1.1em; opacity: 0.85;">隐身无头浏览器渲染 API——可自托管于 Docker 或物理机。</p>
    <p style="margin: 0.4em 0 0 0;">
      <a href="https://pypi.org/project/veilrender/"><img src="https://img.shields.io/pypi/v/veilrender?color=green" alt="PyPI"></a>
      <a href="https://github.com/Oaklight/veilrender/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/veilrender?color=green" alt="Release"></a>
      <a href="https://hub.docker.com/r/oaklight/veilrender"><img src="https://img.shields.io/docker/pulls/oaklight/veilrender?color=blue" alt="Docker Pulls"></a>
      <a href="https://github.com/Oaklight/veilrender/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT"></a>
    </p>
  </div>
</div>

---

VeilRender 接收一个 URL，使用隐身无头浏览器渲染页面，并返回完整内容（HTML、Markdown、readability 提取的文章）。专为 JavaScript 渲染页面或反爬站点的 fetch 降级方案设计。

## 功能特性

- **隐身渲染** — CloakBrowser（71 个 C++ 指纹补丁）+ Patchright（隐身 Playwright 分支）
- **多种输出格式** — HTML、Markdown 和 readability 提取的文章文本
- **页面截图** — 全页面或视口截图，输出 PNG
- **混合浏览器后端** — Chromium (CDP) 和 Firefox/Camoufox (Playwright 协议) 在同一个池中运行
- **水平扩展** — Gateway + 远程浏览器 Worker 池，支持健康检查与自动重连
- **渲染缓存** — L1 内存缓存 + L2 S3 兼容存储（R2、Oracle、AWS）
- **广告/追踪拦截** — 使用 StevenBlack/hosts 的 82k 域名黑名单
- **CDP 代理** — 通过 `/cdp` 直接 WebSocket 访问浏览器
- **Prometheus 指标** — `/metrics` 端点，包含延迟分位数、每 Worker 指标
- **认证** — 可选的 Bearer token 认证
- **自托管** — 部署到 Docker 或物理机
- **仪表盘** — 内置统计仪表盘，访问 `/` 即可查看
- **零外部依赖**（除 Patchright 外）— HTTP 服务器、S3 客户端、HTML 解析全部内置

## 下一步

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } **快速上手**

    ---

    安装 VeilRender 并发送第一个请求。

    [:octicons-arrow-right-24: 安装指南](getting-started/installation.md)

- :material-api:{ .lg .middle } **API 参考**

    ---

    查看可用的端点和参数。

    [:octicons-arrow-right-24: API 文档](api/index.md)

- :material-server:{ .lg .middle } **部署**

    ---

    部署到 Docker、HF Spaces 或物理机。

    [:octicons-arrow-right-24: 部署指南](deployment/index.md)

- :material-cog:{ .lg .middle } **配置**

    ---

    通过环境变量配置 VeilRender。

    [:octicons-arrow-right-24: 配置说明](configuration.md)

</div>
