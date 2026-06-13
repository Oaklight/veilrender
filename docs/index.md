---
title: Home
hide:
  - navigation
---

<div style="display: flex; align-items: center; gap: 1.5em; margin-bottom: 0.5em;">
  <div>
    <h1 style="margin: 0 0 0.2em 0;">VeilRender</h1>
    <p style="margin: 0; font-size: 1.1em; opacity: 0.85;">Headless browser rendering API — self-hostable on HF Spaces, Docker, or bare metal.</p>
    <p style="margin: 0.4em 0 0 0;">
      <a href="https://pypi.org/project/veilrender/"><img src="https://img.shields.io/pypi/v/veilrender?color=green" alt="PyPI"></a>
      <a href="https://github.com/Oaklight/veilrender/releases/latest"><img src="https://img.shields.io/github/v/release/Oaklight/veilrender?color=green" alt="Release"></a>
      <a href="https://hub.docker.com/r/oaklight/veilrender"><img src="https://img.shields.io/docker/pulls/oaklight/veilrender?color=blue" alt="Docker Pulls"></a>
      <a href="https://github.com/Oaklight/veilrender/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT"></a>
      <a href="https://oaklight-veilrender-public.hf.space"><img src="https://img.shields.io/badge/%F0%9F%A4%97-Live_Demo-blue" alt="Live Demo"></a>
    </p>
  </div>
</div>

---

VeilRender accepts a URL and returns the fully rendered page content (HTML, Markdown, readability-extracted article) using a headless Chromium browser. Designed as a fallback for fetch tools that fail on JavaScript-rendered pages.

## Try it now

No authentication needed:

```bash
curl -X POST https://oaklight-veilrender-public.hf.space/render \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Features

- **Multiple output formats** — HTML, Markdown, and readability-extracted article text
- **Screenshot capture** — Full-page or viewport screenshots as PNG
- **Authentication** — Optional Bearer token authentication
- **Concurrency control** — Configurable max concurrent browser contexts
- **Self-hostable** — Deploy on HF Spaces, Docker, or bare metal
- **Dashboard** — Built-in stats dashboard at `/`

## Next steps

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Install VeilRender and make your first request.

    [:octicons-arrow-right-24: Installation](getting-started/installation.md)

- :material-api:{ .lg .middle } **API Reference**

    ---

    Explore the available endpoints and parameters.

    [:octicons-arrow-right-24: API docs](api/index.md)

- :material-server:{ .lg .middle } **Deployment**

    ---

    Deploy to Docker, HF Spaces, or bare metal.

    [:octicons-arrow-right-24: Deployment guide](deployment/index.md)

- :material-cog:{ .lg .middle } **Configuration**

    ---

    Configure VeilRender via environment variables.

    [:octicons-arrow-right-24: Configuration](configuration.md)

</div>
