#!/usr/bin/env python3
"""
Day 29: Benchmark Setup (a fair, repeatable measurement harness)
===============================================================

Problem: "It feels fast" is not data. Before comparing your TSDB to InfluxDB — or
even to itself across changes — you need a HARNESS that measures honestly: warm up
first (skip cold-start noise), repeat the operation many times, and summarize with
statistics that expose the tail (mean lies; p95 tells the truth). Build that harness
once so every later benchmark reuses it.

Learning Objectives:
- Separate the harness (measures) from the target (is measured) — inject both
- Warm up before timing to exclude one-time costs (imports, JIT, cache fill)
- Collect per-iteration samples and summarize: mean/median/stddev/p95, ops/sec
- Make timing DETERMINISTIC in tests by injecting a fake clock
- Compute a speedup ratio to compare two results

Real-World Connection:
Every serious benchmark (influxdb's `inch`/`tsbs`, Go's `testing.B`, pytest-benchmark)
follows this shape: warmup, repeated trials, and a statistical summary — never a single
stopwatch reading. Reporting p95 alongside the mean is standard because tail latency is
what users actually feel.
"""

from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from typing import Callable, List, Protocol


class Timer(Protocol):
    """A monotonic timer. perf_counter() returns seconds as a float."""
    def perf_counter(self) -> float: ...


@dataclass
class BenchmarkResult:
    """Per-iteration timing samples (seconds) plus derived statistics."""
    name: str
    samples: List[float] = field(default_factory=list)

    @property
    def iterations(self) -> int:
        return len(self.samples)

    @property
    def total_time(self) -> float:
        """Sum of all sample durations."""
        # TODO: return sum(self.samples)
        raise NotImplementedError

    @property
    def mean(self) -> float:
        """Mean latency. Use statistics.mean (assume >= 1 sample)."""
        # TODO
        raise NotImplementedError

    @property
    def median(self) -> float:
        """Median latency (statistics.median)."""
        # TODO
        raise NotImplementedError

    @property
    def stddev(self) -> float:
        """Population standard deviation (statistics.pstdev — safe for n == 1 -> 0.0)."""
        # TODO
        raise NotImplementedError

    @property
    def p95(self) -> float:
        """
        95th percentile via linear interpolation (same method as Week 3 Day 17):
            sort samples; rank = 0.95 * (n - 1); interpolate floor/ceil.
        """
        # TODO: sort, compute fractional rank, interpolate
        raise NotImplementedError

    @property
    def min(self) -> float:
        # TODO
        raise NotImplementedError

    @property
    def max(self) -> float:
        # TODO
        raise NotImplementedError

    @property
    def ops_per_sec(self) -> float:
        """Throughput = iterations / total_time (0.0 if total_time == 0)."""
        # TODO
        raise NotImplementedError


class Benchmark:
    """
    Times a zero-argument callable. Injected timer makes results deterministic in tests.
    """

    def __init__(self, timer: Timer):
        self.timer = timer

    def run(self, name: str, fn: Callable[[], None], iterations: int, warmup: int = 0) -> BenchmarkResult:
        """
        Run `fn`:
          - call it `warmup` times WITHOUT timing (discard cold-start noise)
          - then call it `iterations` times, timing each with the injected timer
            (start = perf_counter(); fn(); end = perf_counter(); sample = end - start)
        Return a BenchmarkResult holding the `iterations` samples.
        """
        # TODO: run warmup (untimed), then time each measured iteration and collect samples.
        raise NotImplementedError

    @staticmethod
    def speedup(faster: BenchmarkResult, slower: BenchmarkResult) -> float:
        """
        How many times faster `faster` is than `slower`, by mean latency:
            slower.mean / faster.mean   (0.0 if faster.mean == 0)
        """
        # TODO
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Fake timer for deterministic tests
# ---------------------------------------------------------------------------
class FakeTimer:
    """perf_counter() returns successive scripted values (repeats the last if exhausted)."""
    def __init__(self, times: List[float]):
        self._times = list(times)
        self._last = times[0] if times else 0.0

    def perf_counter(self) -> float:
        if self._times:
            self._last = self._times.pop(0)
        return self._last


def test_benchmark_setup():
    print("Testing Benchmark Setup...")

    # A timer scripted so measured durations are exactly [1, 2, 3, 4] seconds.
    # run() calls perf_counter twice per measured iteration (start, end).
    timer = FakeTimer([0, 1, 0, 2, 0, 3, 0, 4])
    calls = {"n": 0}
    bench = Benchmark(timer)
    res = bench.run("op", fn=lambda: calls.__setitem__("n", calls["n"] + 1), iterations=4)

    # Test 1: correct number of samples and fn calls
    assert res.iterations == 4 and calls["n"] == 4
    print("✓ Test 1 passed: iterations recorded")

    # Test 2: samples are the measured durations
    assert res.samples == [1, 2, 3, 4]
    print("✓ Test 2 passed: per-iteration durations")

    # Test 3: mean / median / total
    assert res.mean == 2.5 and res.median == 2.5 and res.total_time == 10
    print("✓ Test 3 passed: mean/median/total")

    # Test 4: min / max / stddev
    assert res.min == 1 and res.max == 4
    assert abs(res.stddev - statistics.pstdev([1, 2, 3, 4])) < 1e-12
    print("✓ Test 4 passed: min/max/stddev")

    # Test 5: p95 interpolation. rank = 0.95*3 = 2.85 -> 3 + 0.85*(4-3) = 3.85
    assert abs(res.p95 - 3.85) < 1e-9
    print("✓ Test 5 passed: p95")

    # Test 6: ops_per_sec = iterations / total_time = 4 / 10
    assert abs(res.ops_per_sec - 0.4) < 1e-9
    print("✓ Test 6 passed: ops_per_sec")

    # Test 7: warmup runs fn but is NOT timed
    t2 = FakeTimer([0, 1, 0, 2])  # only 2 measured iterations worth of ticks
    c2 = {"n": 0}
    r2 = Benchmark(t2).run("op", lambda: c2.__setitem__("n", c2["n"] + 1), iterations=2, warmup=3)
    assert r2.iterations == 2 and c2["n"] == 5  # 3 warmup + 2 measured
    print("✓ Test 7 passed: warmup untimed")

    # Test 8: speedup ratio by mean latency
    fast = BenchmarkResult("fast", [1, 1, 1, 1])   # mean 1
    slow = BenchmarkResult("slow", [4, 4, 4, 4])   # mean 4
    assert Benchmark.speedup(fast, slow) == 4.0
    print("✓ Test 8 passed: speedup ratio")

    print("\n🎉 All benchmark setup tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement the BenchmarkResult properties and Benchmark.run / speedup.
    2. Run: python day29_benchmark_setup.py
    3. All 8 tests should pass.

    Success criteria:
    - run() warms up untimed, then collects exactly `iterations` samples
    - statistics (mean/median/stddev/p95/min/max/ops_per_sec) are correct
    - timing is deterministic under the injected FakeTimer
    - speedup compares two results by mean latency

    Next steps:
    - Day 30: point this harness at write operations across batch sizes.
    - Think about: why report p95 as well as the mean? What does mean << p95 imply?
    """
    test_benchmark_setup()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Harness vs Target
   - The thing that MEASURES must be separate from the thing MEASURED. Injecting the
     target callable (and the timer) lets one harness benchmark writes, queries, or a
     fake with known timing — and makes tests deterministic.

2. Warmup
   - The first few runs pay one-time costs (imports, cache fill, allocator warmup).
     Timing them pollutes the average. Discarding warmup iterations measures steady
     state, which is what you actually care about.

3. Repeated Trials + Statistics
   - One measurement is noise. Many samples + a summary (mean, median, stddev, p95)
     characterize the distribution. Median resists outliers; stddev shows variance; p95
     exposes the tail the mean hides.

4. Determinism in Tests
   - Real clocks make tests flaky. An injected FakeTimer returns scripted durations so
     you can assert exact statistics — the same dependency-injection discipline used for
     the clock in Week 4 Day 28.

Connection to InfluxDB:
- InfluxDB's benchmarking tools (inch, tsbs) and Go's testing.B all warm up, repeat, and
  report distributions. p50/p95/p99 latency is the standard way TSDB performance is
  quoted because tail latency drives dashboards and alerts.

Trade-offs:
- More iterations = more stable numbers but longer runs. Warmup improves fidelity but
  costs time. Wall-clock timing is realistic but noisy; a fixed number of trials plus
  robust statistics (median/p95) is the practical compromise.
"""
