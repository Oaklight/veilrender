"""In-memory request statistics.

All counters are safe to mutate without locks because asyncio
is single-threaded cooperative multitasking.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

_start_time: float = time.monotonic()


@dataclass
class EndpointStats:
    """Per-endpoint request counters and latency tracking."""

    requests: int = 0
    successes: int = 0
    failures: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_ms: float = 0.0
    _latencies: deque[float] = field(default_factory=lambda: deque(maxlen=1000))

    def record_success(self, elapsed_ms: float) -> None:
        """Record a successful request."""
        self.successes += 1
        self.total_ms += elapsed_ms
        self._latencies.append(elapsed_ms)

    def record_failure(self, elapsed_ms: float) -> None:
        """Record a failed request."""
        self.failures += 1
        self.total_ms += elapsed_ms
        self._latencies.append(elapsed_ms)

    @property
    def avg_ms(self) -> float:
        """Average latency in milliseconds."""
        total = self.successes + self.failures
        return self.total_ms / total if total > 0 else 0.0

    def _percentile(self, q: float) -> float:
        """Compute a percentile from the latency window."""
        if not self._latencies:
            return 0.0
        sorted_lat = sorted(self._latencies)
        idx = int(len(sorted_lat) * q)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def p50_ms(self) -> float:
        """50th percentile (median) latency in milliseconds."""
        return self._percentile(0.50)

    @property
    def p95_ms(self) -> float:
        """95th percentile latency in milliseconds."""
        return self._percentile(0.95)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        total = self.successes + self.failures
        return (self.successes / total * 100) if total > 0 else 0.0


render = EndpointStats()
screenshot = EndpointStats()


def uptime_seconds() -> float:
    """Seconds since the process started."""
    return time.monotonic() - _start_time


def format_uptime() -> str:
    """Human-readable uptime string."""
    secs = int(uptime_seconds())
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    mins, secs = divmod(secs, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)
