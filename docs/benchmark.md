---
title: 性能测试
---

# 性能测试

在 HF Spaces（免费版，2 vCPU）和自托管 VPS（3 vCPU，容器限制 1 GB）上测试，每个目标 46 次请求**成功率 100%**。

## 测试结果

| 测试项 | HF Spaces | 自托管 VPS |
|--------|-----------|------------|
| 顺序 × 5（混合 URL） | 总计 8.72 s | 总计 11.81 s |
| 并发 × 10（混合 URL） | 1.40 – 9.37 s | 1.29 – 13.45 s |
| 连续 × 20（顺序） | 平均 0.885 s | 平均 1.029 s |
| 容器内存峰值 | — | 614 MiB / 1 GB |

完整测试数据：[GitHub 上的 BENCHMARK.md](https://github.com/Oaklight/veilrender/blob/master/BENCHMARK.md)
