---
title: 更新日志
---

# 更新日志

## v0.2.0

- **新功能**: `GET /` 统计仪表盘，包含徽章、容量条和响应式布局
- **新功能**: 公开 HF Space（无需认证）和在线演示徽章
- **改进**: 默认 `max_concurrent` 从 3 提升到 5
- **修复**: 以运行时用户预下载 Chromium，避免启动时重复下载
- **基建**: CI 工作流拆分为 ci、release 和 deploy-hf
- **基建**: 添加 PyPI 发布工作流、Docker Hub / GHCR 多架构镜像
- **基建**: 添加性能测试结果

## v0.1.0

- 初始发布：无头浏览器渲染 API
- `POST /render` — 将 URL 渲染为 HTML、Markdown、readability
- `POST /screenshot` — 截取页面截图
- `GET /health` — 健康检查端点
- Docker 支持，多架构镜像
- HF Spaces 部署支持
- 通过环境变量配置
