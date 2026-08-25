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
```

Since v0.4.0, VeilRender auto-downloads CloakBrowser on first run—no manual browser install needed.

For custom setups, set `CLOAKBROWSER_BINARY` to point to your own browser binary, or set `CLOAKBROWSER_MIRROR` to a GitHub mirror URL (e.g. `https://ghfast.top`) for faster downloads in China. See [Configuration](../configuration.md#browser-binary) for details.

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
