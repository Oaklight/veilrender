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
```

自 v0.4.0 起，VeilRender 在首次运行时会自动下载 CloakBrowser，无需手动安装浏览器。

如需自定义设置，可设置 `CLOAKBROWSER_BINARY` 指向自有浏览器二进制文件，或设置 `CLOAKBROWSER_MIRROR` 为 GitHub 镜像 URL（如 `https://ghfast.top`）以加速国内下载。详见 [配置](../configuration.md#浏览器二进制文件)。

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
