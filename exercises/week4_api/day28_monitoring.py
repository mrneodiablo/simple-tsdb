#!/usr/bin/env python3
"""
Day 28: Performance Monitoring (per-operation metrics, low overhead)
===================================================================

Problem: You can't optimize what you can't measure. A server needs to know its own
health: how many queries ran, how long they took (mean AND tail latency), how many
failed, and its throughput. Build a lightweight metrics collector that times
operations via an injected clock and reports per-operation statistics — the same
p50/p95 tail thinking from Day 17, now pointed at the database itself.

Learning Objectives:
- Time operations with an injected clock (testable, deterministic)
- Accumulate per-operation stats: count, errors, latencies
- Derive mean/p95 latency, error rate, and throughput from raw samples
- Provide a context manager so instrumenting code is one `with` line
- Keep overhead low and the collector dependency-injected

Real-World Connection:
Databases expose self-metrics: InfluxDB has `_internal` measurements, Prometheus
exporters emit request counts and latency histograms, and every RPC framework tracks
p50/p95/p99 + error rate. This is the observability layer that makes production
debugging possible.
"""

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
        raise NotImplementedError

    @property
    def mean_latency(self) -> Optional[float]:
        """Average latency, or None if no samples."""
        # TODO
        raise NotImplementedError

    @property
    def p95_latency(self) -> Optional[float]:
        """
        95th-percentile latency via linear interpolation (same method as Day 17):
            sort samples; rank = 0.95 * (n - 1); interpolate between floor/ceil.
        Return None if there are no samples.
        """
        # TODO: implement the exact-percentile interpolation for p=95
        raise NotImplementedError

    @property
    def error_rate(self) -> float:
        """errors / count, or 0.0 when count == 0."""
        # TODO
        raise NotImplementedError

    @property
    def throughput(self) -> float:
        """
        Operations per second of busy time: count / total_time.
        Return 0.0 when total_time == 0 (avoid divide-by-zero).
        """
        # TODO
        raise NotImplementedError


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
        raise NotImplementedError

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


# ---------------------------------------------------------------------------
# Fake clock for testing (no real time)
# ---------------------------------------------------------------------------
class FakeClock:
    """now() returns successive values from `times` (repeats the last one if exhausted)."""
    def __init__(self, times: List[float]):
        self._times = list(times)
        self._last = times[0] if times else 0.0

    def now(self) -> float:
        if self._times:
            self._last = self._times.pop(0)
        return self._last


def test_monitoring():
    print("Testing Performance Monitoring...")

    mc = MetricsCollector(FakeClock([0.0]))

    # Test 1: record accumulates count
    for d in [0.1, 0.2, 0.3, 0.4]:
        mc.record("query", d)
    assert mc.stats("query").count == 4
    print("✓ Test 1 passed: count")

    # Test 2: mean latency
    assert abs(mc.stats("query").mean_latency - 0.25) < 1e-9
    print("✓ Test 2 passed: mean latency")

    # Test 3: p95 latency (interpolation)
    s = MetricsCollector(FakeClock([0.0]))
    for d in [float(i) for i in range(1, 101)]:  # 1..100
        s.record("q", d)
    p95 = s.stats("q").p95_latency
    assert 94 <= p95 <= 96, f"p95 was {p95}"
    print(f"✓ Test 3 passed: p95 latency = {p95}")

    # Test 4: error rate
    m = MetricsCollector(FakeClock([0.0]))
    m.record("q", 0.1)
    m.record("q", 0.1, error=True)
    m.record("q", 0.1, error=True)
    m.record("q", 0.1)
    assert abs(m.stats("q").error_rate - 0.5) < 1e-9
    print("✓ Test 4 passed: error rate")

    # Test 5: throughput = count / total_time
    st = mc.stats("query")  # 4 ops, total 1.0s
    assert abs(st.total_time - 1.0) < 1e-9
    assert abs(st.throughput - 4.0) < 1e-9
    print("✓ Test 5 passed: throughput")

    # Test 6: measure() times via the injected clock
    timed = MetricsCollector(FakeClock([10.0, 10.25]))  # enter=10.0, exit=10.25
    with timed.measure("op"):
        pass
    assert abs(timed.stats("op").latencies[0] - 0.25) < 1e-9
    assert timed.stats("op").errors == 0
    print("✓ Test 6 passed: measure() timing")

    # Test 7: measure() records an error when the block raises (and re-raises)
    err = MetricsCollector(FakeClock([1.0, 1.5]))
    try:
        with err.measure("op"):
            raise RuntimeError("boom")
        assert False, "exception should propagate"
    except RuntimeError:
        pass
    assert err.stats("op").errors == 1 and err.stats("op").count == 1
    print("✓ Test 7 passed: measure() error tracking")

    # Test 8: operations tracked separately; empty stats for unknown op
    mm = MetricsCollector(FakeClock([0.0]))
    mm.record("read", 0.1)
    mm.record("write", 0.2)
    assert mm.operations() == ["read", "write"]
    assert mm.stats("unknown").count == 0 and mm.stats("unknown").mean_latency is None
    print("✓ Test 8 passed: per-operation isolation")

    print("\n🎉 All monitoring tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement the OpStats properties and MetricsCollector.record.
    2. Run: python day28_monitoring.py
    3. All 8 tests should pass.

    Success criteria:
    - record/measure accumulate per-operation count, errors, and latencies
    - mean and p95 latency, error rate, and throughput are derived correctly
    - measure() times via the injected clock and flags errors without suppressing them
    - unknown operations report empty stats, not a crash

    Next steps:
    - Run the Week 4 Integration Lab: labs/week4_lab.py (full system over a real socket).
    - Think about: why report p95 (tail) latency alongside the mean? What does a big
      gap between them tell you?
    """
    test_monitoring()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Observability
   - A server that can't report its own count/latency/errors is a black box in
     production. Cheap, always-on metrics are the difference between "the DB is slow"
     and "QUERY p95 jumped to 800ms at 14:03 with a 12% error rate".

2. Tail Latency Matters
   - The mean hides pain: if p95 is 10x the mean, most requests are fine but a critical
     slice is suffering. Tracking p95/p99 (Day 17's percentiles, reused) is standard for
     any latency-sensitive service.

3. Injected Clock
   - Timing against an injected Clock makes tests deterministic (no sleep, no
     flakiness) and lets you swap monotonic vs wall clocks. The context manager keeps
     the call site to a single `with collector.measure("query"):` line — low friction,
     low overhead.

4. Per-Operation Breakdown
   - Aggregating by operation name (read vs write vs query) localizes problems. One slow
     operation type won't be masked by fast ones in a global average.

Connection to InfluxDB:
- InfluxDB records internal metrics to a `_internal` database; exporters and RPC layers
  everywhere emit request counts + latency histograms + error counters. You just built
  the collector behind that.

Trade-offs:
- Storing every latency sample gives exact percentiles but grows unbounded; production
  collectors use fixed-size histograms/reservoirs (Day 17's HistogramQuantile) or
  sliding windows to cap memory. Exact samples are fine for this learning server.
"""
