---
title: Deployment
---

# Deployment

VeilRender supports two deployment modes:

- **Single Instance** — Use the full image (`oaklight/veilrender:latest`) with CloakBrowser embedded. Simplest setup for moderate workloads.
- **Gateway + Worker Pool** — Use the gateway image (`oaklight/veilrender:gateway`) in front of dedicated browser workers for horizontal scaling and mixed browser engines.

Deployment methods:

- **[Docker](docker.md)** — Recommended for production
- **[HF Spaces](hf-spaces.md)** — Free hosting with Hugging Face
- **[Bare Metal](bare-metal.md)** — Direct installation on a server
