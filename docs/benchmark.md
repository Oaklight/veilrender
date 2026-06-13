---
title: Benchmark
---

# Benchmark

Performance tested on HF Spaces (free tier, 2 vCPU) and a self-hosted VPS (3 vCPU, 1 GB container). **100% success rate** across all 46 requests per target.

## Results

| Test | HF Spaces | Self-hosted |
|------|-----------|-------------|
| Sequential × 5 (mixed URLs) | 8.72 s total | 11.81 s total |
| Concurrent × 10 (mixed URLs) | 1.40 – 9.37 s | 1.29 – 13.45 s |
| Rapid-fire × 20 (sequential) | 0.885 s avg | 1.029 s avg |
| Peak container memory | — | 614 MiB / 1 GB |

Full benchmark details: [BENCHMARK.md on GitHub](https://github.com/Oaklight/veilrender/blob/master/BENCHMARK.md)
