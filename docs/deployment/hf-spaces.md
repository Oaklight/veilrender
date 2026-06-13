---
title: HF Spaces
---

# Hugging Face Spaces Deployment

VeilRender can be deployed as a free Docker Space on Hugging Face.

## Public demo

A public instance (no auth) is available at:

<https://oaklight-veilrender-public.hf.space>

## Deploy your own

1. Create a new Space on [Hugging Face](https://huggingface.co/new-space)
2. Select **Docker** as the SDK
3. Set the repository to `Oaklight/veilrender` or use the Docker image `oaklight/veilrender`
4. Configure secrets:
    - `VEILRENDER_API_TOKEN` — your API token (optional; omit for public access)

## Notes

- HF Spaces free tier provides 2 vCPU
- The Space will sleep after inactivity and wake on the next request
- See [Benchmark](../benchmark.md) for performance numbers on HF Spaces
