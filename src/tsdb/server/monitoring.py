#!/usr/bin/env python3

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol


class Clock(Protocol):
    """A monotonic clock. now() returns seconds as a float."""
    def now(self) -> float: ...


@dataclass
class OpStats:
    """Raw samples for one operation plus derived statistics."""
    count: int = 0
    errors: int = 0
    latencies: List[float] = field(default_factory=list)  # seconds

    @property
    def total_time(self) -> float:
        """Sum of all recorded latencies (seconds)."""
        # TODO: return the sum of self.latencies
        return sum(self.latencies)


    @property
    def mean_latency(self) -> Optional[float]:
        """Average latency, or None if no samples."""
        # TODO
        if self.count == 0:
            return None
        return self.total_time / self.count

    @property
    def p95_latency(self) -> Optional[float]:
        """
        95th-percentile latency via linear interpolation (same method as Day 17):
            sort samples; rank = 0.95 * (n - 1); interpolate between floor/ceil.
        Return None if there are no samples.
        """
        # TODO: implement the exact-percentile interpolation for p=95
        if not self.latencies:
            return None
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        rank = 0.95 * (n - 1)
        lower_index = int(math.floor(rank))
        upper_index = int(math.ceil(rank))
        if lower_index == upper_index:
            return sorted_latencies[lower_index]
        lower_value = sorted_latencies[lower_index]
        upper_value = sorted_latencies[upper_index]
        weight = rank - lower_index
        return lower_value + weight * (upper_value - lower_value)

    @property
    def error_rate(self) -> float:
        """errors / count, or 0.0 when count == 0."""
        # TODO
        if self.count == 0:
            return 0.0
        return self.errors / self.count

    @property
    def throughput(self) -> float:
        """
        Operations per second of busy time: count / total_time.
        Return 0.0 when total_time == 0 (avoid divide-by-zero).
        """
        # TODO
        if self.total_time == 0:
            return 0.0
        return self.count / self.total_time


class MetricsCollector:
    """
    Collects per-operation metrics. Time operations with `measure()` (uses the
    injected clock) or record durations directly with `record()`.

    Dependency injected:
      - clock: something with now() -> float (inject a fake in tests)
    """

    def __init__(self, clock: Clock):
        self.clock = clock
        self._stats: Dict[str, OpStats] = {}

    def record(self, operation: str, duration: float, error: bool = False) -> None:
        """
        Record one observation for `operation`: bump count, add the latency sample,
        and bump errors when error is True. Create the OpStats entry on first use.
        """
        # TODO: get-or-create self._stats[operation]; append duration; count; errors.
        if operation not in self._stats:
            self._stats[operation] = OpStats()
        op_stats = self._stats[operation]
        op_stats.count += 1
        op_stats.latencies.append(duration)
        if error:
            op_stats.errors += 1

    def stats(self, operation: str) -> OpStats:
        """Return the OpStats for an operation (empty OpStats if never seen)."""
        return self._stats.get(operation, OpStats())

    def operations(self) -> List[str]:
        """Names of all tracked operations, sorted."""
        return sorted(self._stats)

    def measure(self, operation: str) -> "_Measure":
        """Context manager that times the block and records it (errors auto-detected)."""
        return _Measure(self, operation)


class _Measure:
    """Context manager: times a block via the collector's clock and records it. (GIVEN)"""
    def __init__(self, collector: MetricsCollector, operation: str):
        self.collector = collector
        self.operation = operation
        self.start = 0.0

    def __enter__(self) -> "_Measure":
        self.start = self.collector.clock.now()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        duration = self.collector.clock.now() - self.start
        self.collector.record(self.operation, duration, error=exc_type is not None)
        return False  # never suppress exceptions

