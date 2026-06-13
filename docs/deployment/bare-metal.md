---
title: 物理机部署
---

# 物理机部署

直接在服务器上运行 VeilRender，无需容器。

## 前置条件

- Python 3.10+
- Chromium 系统依赖（因操作系统而异）

## 安装

```bash
pip install veilrender
playwright install chromium
```

## 运行

```bash
export VEILRENDER_API_TOKEN=your-secret
python -m veilrender
```

服务默认绑定到 `0.0.0.0:7860`。详见 [配置](../configuration.md)。

## Systemd 服务（可选）

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
