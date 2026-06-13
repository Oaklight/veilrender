---
title: 首页
hide:
  - navigation
---

<div style="display: flex; align-items: center; gap: 1.5em; margin-bottom: 0.5em;">
  <div>
    <h1 style="margin: 0 0 0.2em 0;">VeilRender</h1>
    <p style="margin: 0; font-size: 1.1em; opacity: 0.85;">无头浏览器渲染 API——可自托管于 HF Spaces、Docker 或物理机。</p>
    <p style="margin: 0.4em 0 0 0;">
      <a href="https://pypi.org/project/veilrender/"><img src="https://img.shields.io/pypi/v/veilrender?color=green" alt="PyPI"></a>
      <a href="https://github.com/Oaklight/veilrender/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/veilrender?color=green" alt="Release"></a>
      <a href="https://hub.docker.com/r/oaklight/veilrender"><img src="https://img.shields.io/docker/pulls/oaklight/veilrender?color=blue" alt="Docker Pulls"></a>
      <a href="https://github.com/Oaklight/veilrender/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT"></a>
      <a href="https://oaklight-veilrender-public.hf.space"><img src="https://img.shields.io/badge/%F0%9F%A4%97-在线演示-blue" alt="在线演示"></a>
    </p>
  </div>
</div>

---

VeilRender 接收一个 URL，使用无头 Chromium 浏览器渲染页面，并返回完整内容（HTML、Markdown、readability 提取的文章）。专为 JavaScript 渲染页面的 fetch 降级方案设计。

## 在线试用

无需认证：

```bash
curl -X POST https://oaklight-veilrender-public.hf.space/render \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## 功能特性

- **多种输出格式** — HTML、Markdown 和 readability 提取的文章文本
- **页面截图** — 全页面或视口截图，输出 PNG
- **认证** — 可选的 Bearer token 认证
- **并发控制** — 可配置最大并发浏览器上下文数
- **自托管** — 部署到 HF Spaces、Docker 或物理机
- **仪表盘** — 内置统计仪表盘，访问 `/` 即可查看

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
