---
title: Installation
---

# Installation

VeilRender can be installed via pip or run as a Docker container.

## Install with pip

```bash
pip install veilrender
```

VeilRender uses [CloakBrowser](https://github.com/Oaklight/cloakbrowser) under the hood, which requires Chromium. Install it with:

```bash
playwright install chromium
```

## Install with Docker

Pull the official image from Docker Hub:

```bash
docker pull oaklight/veilrender
```

Or from GitHub Container Registry:

```bash
docker pull ghcr.io/oaklight/veilrender
```

## For development

Clone the repository and install in development mode:

```bash
git clone https://github.com/Oaklight/veilrender.git
cd veilrender
pip install -e ".[dev]"
playwright install chromium
```
