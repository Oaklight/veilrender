# VeilRender

[![PyPI version](https://img.shields.io/pypi/v/veilrender?color=green)](https://pypi.org/project/veilrender/)
[![GitHub release](https://img.shields.io/github/v/release/Oaklight/veilrender?color=green)](https://github.com/Oaklight/veilrender/releases/latest)
[![CI](https://github.com/Oaklight/veilrender/actions/workflows/ci.yml/badge.svg)](https://github.com/Oaklight/veilrender/actions/workflows/ci.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/oaklight/veilrender?color=blue)](https://hub.docker.com/r/oaklight/veilrender)
[![Docker Image](https://img.shields.io/docker/v/oaklight/veilrender?sort=semver&label=docker&color=blue)](https://hub.docker.com/r/oaklight/veilrender)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![HF Spaces](https://img.shields.io/badge/%F0%9F%A4%97-Spaces-blue)](https://huggingface.co/spaces/oaklight/veilrender)

**中文** | [English](README_en.md)

无头浏览器渲染 API——可自托管于 HF Spaces、Docker 或物理机。

VeilRender 接收一个 URL，使用无头 Chromium 浏览器渲染页面，并返回完整内容（HTML、Markdown、readability 提取的文章）。专为 JavaScript 渲染页面的 fetch 降级方案设计。

## 快速开始

### Docker

```bash
docker run -p 7860:7860 -e VEILRENDER_API_TOKEN=your-secret oaklight/veilrender
```

### 本地开发

```bash
pip install -e ".[dev]"
playwright install chromium
python -m veilrender
```

## API

### GET /health

服务运行中返回 `{"status": "ok"}`。

### POST /render

渲染指定 URL 并返回页面内容。

```bash
curl -X POST http://localhost:7860/render \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

响应：

```json
{
  "content": {
    "html": "...",
    "markdown": "...",
    "readability": "..."
  },
  "metadata": {
    "title": "Example Domain",
    "url": "https://example.com",
    "status_code": 200
  },
  "links": [{"url": "https://www.iana.org/domains/example", "text": "More information..."}]
}
```

### POST /screenshot

截取指定 URL 的页面截图。

```bash
curl -X POST http://localhost:7860/screenshot \
  -H "Authorization: Bearer your-secret" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png
```

## 配置

所有设置通过 `VEILRENDER_` 前缀的环境变量配置：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VEILRENDER_API_TOKEN` | *(无)* | API 认证令牌。未设置时认证关闭。 |
| `VEILRENDER_PORT` | `7860` | 服务端口 |
| `VEILRENDER_HOST` | `0.0.0.0` | 服务绑定地址 |
| `VEILRENDER_TIMEOUT` | `30000` | 浏览器导航超时（毫秒） |
| `VEILRENDER_VIEWPORT_WIDTH` | `1280` | 浏览器视口宽度 |
| `VEILRENDER_VIEWPORT_HEIGHT` | `720` | 浏览器视口高度 |
| `VEILRENDER_MAX_CONCURRENT` | `3` | 最大并发浏览器上下文数 |

## 性能测试

在 HF Spaces（免费版，2 vCPU）和自托管 VPS（3 vCPU，容器限制 1 GB）上测试，每个目标 46 次请求**成功率 100%**。

| 测试项 | HF Spaces | 自托管 VPS |
|--------|-----------|------------|
| 顺序 × 5（混合 URL） | 总计 8.72 s | 总计 11.81 s |
| 并发 × 10（混合 URL） | 1.40 – 9.37 s | 1.29 – 13.45 s |
| 连续 × 20（顺序） | 平均 0.885 s | 平均 1.029 s |
| 容器内存峰值 | — | 614 MiB / 1 GB |

完整结果：[BENCHMARK.md](BENCHMARK.md)

## 许可证

MIT
