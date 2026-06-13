# Benchmark Results

Stress test of VeilRender across two deployment targets, measured from a single client host.

**Date**: 2026-06-12

## Test Environment

| | HF Spaces (free tier) | Self-hosted VPS |
|---|---|---|
| **CPU** | 2 vCPU (shared) | 3 vCPU Intel Xeon E5-2699 v4 @ 2.20 GHz (shared) |
| **Memory** | 16 GB (shared) | 1 GB (container limit, 3.8 GB host) |
| **OS / Runtime** | Docker (HF-managed) | Docker on Debian 12 |
| **Region** | US (AWS) | US East |
| **VeilRender config** | `MAX_CONCURRENT=3`, default timeout | same |

## Test URLs

| Label | URL | Complexity |
|-------|-----|------------|
| example.com | `https://example.com` | Minimal static HTML |
| httpbin | `https://httpbin.org/html` | Small static page |
| Wikipedia | `https://en.wikipedia.org/wiki/Headless_browser` | Heavy JS + 300 KB HTML |
| HackerNews | `https://news.ycombinator.com` | Dynamic content |
| GitHub | `https://github.com/Oaklight/veilrender` | JS-heavy SPA |

## Success Rate

| Test | Requests | HF Spaces | Self-hosted |
|------|----------|-----------|-------------|
| Sequential (5 URLs) | 5 | ✅ 5/5 | ✅ 5/5 |
| Concurrent × 3 | 3 | ✅ 3/3 | ✅ 3/3 |
| Concurrent × 5 | 5 | ✅ 5/5 | ✅ 5/5 |
| Concurrent × 10 (mixed) | 10 | ✅ 10/10 | ✅ 10/10 |
| Screenshot × 3 | 3 | ✅ 3/3 | ✅ 3/3 |
| Rapid-fire × 20 | 20 | ✅ 20/20 | ✅ 20/20 |
| **Total** | **46** | **46/46 (100%)** | **46/46 (100%)** |

## Response Time

### Sequential Rendering

| URL | HF Spaces | Self-hosted |
|-----|-----------|-------------|
| example.com | 0.99 s | 1.18 s |
| httpbin | 0.89 s | 1.16 s |
| Wikipedia | 1.55 s | 3.13 s |
| HackerNews | 1.24 s | 1.49 s |
| GitHub | 4.06 s | 4.86 s |
| **Total** | **8.72 s** | **11.81 s** |

### Concurrent Rendering (example.com)

| Concurrency | HF Spaces (min / max) | Self-hosted (min / max) |
|-------------|----------------------|------------------------|
| 3 | 1.17 / 1.22 s | 1.10 / 2.06 s |
| 5 | 1.19 / 2.14 s | 1.22 / 3.50 s |

### Concurrent × 10 (mixed URLs)

| | HF Spaces | Self-hosted |
|---|-----------|-------------|
| Fastest | 1.40 s | 1.29 s |
| Slowest | 9.37 s | 13.45 s |
| All succeeded | ✅ | ✅ |

### Rapid-fire × 20 (sequential, example.com)

| | HF Spaces | Self-hosted |
|---|-----------|-------------|
| Average | 0.885 s | 1.029 s |
| Total | 17.71 s | 20.57 s |
| Success | 20/20 | 20/20 |

## Server Load (Self-hosted)

Resource usage of the VeilRender container during the stress test:

| Phase | System Load | Container CPU | Container Memory |
|-------|------------|---------------|-----------------|
| Idle (pre-test) | 0.00 | 0.0% | 368 MiB |
| Concurrent × 10 start | 0.17 | 77.6% | 424 MiB |
| **Concurrent × 10 peak** | **1.64** | **237.4%** | **614 MiB** |
| Rapid-fire × 20 | 1.21 | 80.2% | 508 MiB |
| Post-test cooldown | 1.39 | 0.5% | 486 MiB |

Peak memory stayed well within the 1 GB container limit. No OOM kills observed.

## Key Takeaways

- **100% success rate** on both platforms across all 46 requests per target.
- **HF Spaces was ~25% faster** on sequential workloads and ~30% faster under concurrency, likely due to more CPU headroom.
- **Concurrency queuing works correctly** — requests beyond `MAX_CONCURRENT=3` queue and complete without errors.
- **Self-hosted peak CPU hit 237%** (2+ cores saturated) during 10-concurrent, but recovered quickly with no failures.
- **Memory usage is modest** — peaked at 614 MiB under heavy load, well within a 1 GB container limit.
- HF Spaces free tier has a **cold-start penalty** when the Space has been idle; the self-hosted VPS runs continuously.
