---
title: Bare Metal
---

# Bare Metal Deployment

Run VeilRender directly on a server without containers.

## Prerequisites

- Python 3.10+
- System dependencies for Chromium (varies by OS)

## Installation

```bash
pip install veilrender
playwright install chromium
```

## Run

```bash
export VEILRENDER_API_TOKEN=your-secret
python -m veilrender
```

The server binds to `0.0.0.0:7860` by default. See [Configuration](../configuration.md) for all options.

## Systemd service (optional)

```ini
[Unit]
Description=VeilRender
After=network.target

[Service]
Type=simple
User=veilrender
Environment=VEILRENDER_API_TOKEN=your-secret
ExecStart=/usr/local/bin/python -m veilrender
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
