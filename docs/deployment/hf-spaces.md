---
title: HF Spaces
---

# Hugging Face Spaces 部署

VeilRender 可以作为免费的 Docker Space 部署到 Hugging Face。

## 公开演示

公开实例（无需认证）：

<https://oaklight-veilrender-public.hf.space>

## 部署你自己的实例

1. 在 [Hugging Face](https://huggingface.co/new-space) 创建新 Space
2. 选择 **Docker** 作为 SDK
3. 设置仓库为 `Oaklight/veilrender` 或使用 Docker 镜像 `oaklight/veilrender`
4. 配置 secrets：
    - `VEILRENDER_API_TOKEN` — 你的 API token（可选；不设置则公开访问）

## 注意事项

- HF Spaces 免费版提供 2 vCPU
- Space 在无活动后会休眠，下次请求时自动唤醒
- 性能数据详见 [性能测试](../benchmark.md)
