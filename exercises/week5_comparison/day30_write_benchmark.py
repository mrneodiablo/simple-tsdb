#!/usr/bin/env python3
"""
Day 30: Write Performance (throughput vs batch size)
====================================================

Problem: The single most important write-path lesson in any database is BATCHING.
Writing points one at a time pays fixed per-call overhead (serialization, index
update, fsync intent) every time; writing them in batches amortizes that overhead
across many points, so throughput climbs with batch size — up to a point. Measure
this curve for your Week 1 write path using the Day 29 harness idea, deterministically.

Learning Objectives:
- Generate a reproducible synthetic workload (seeded RNG)
- Measure write throughput (points/sec) as a function of batch size
- Separate total time into per-batch latency and derive throughput
- Show the amortization curve: bigger batches -> higher throughput
- Keep the measured `write_fn` injected so tests are deterministic

Real-World Connection:
InfluxDB's line-protocol write API is explicitly batch-oriented; clients buffer points
and flush in batches of thousands because per-request overhead dominates otherwise. The
throughput-vs-batch-size curve you produce is the standard way to tune a write client.
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Protocol


class Timer(Protocol):
    def perf_counter(self) -> float: ...


Point = Dict[str, Any]
WriteFn = Callable[[List[Point]], None]  # writes one batch of points


class WorkloadGenerator:
    """Deterministic synthetic points (seeded so a benchmark is reproducible)."""

    HOSTS = ["web-01", "web-02", "api-01", "db-01"]
    REGIONS = ["us-west", "us-east", "eu"]

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def generate(self, n: int) -> List[Point]:
        """
        Return `n` points with a monotonic timestamp and random tags/value, using the
        seeded RNG so two generators with the same seed produce identical data.
        """
        # TODO: build n dicts {measurement, timestamp (i), tags{host,region}, fields{value}}
        #       using self._rng.choice / self._rng.uniform.
        raise NotImplementedError


@dataclass
class WriteResult:
    batch_size: int
    total_points: int
    total_time: float
    num_batches: int

    @property
    def throughput(self) -> float:
        """Points per second = total_points / total_time (0.0 if total_time == 0)."""
        # TODO
        raise NotImplementedError

    @property
    def mean_batch_latency(self) -> float:
        """Average time per batch = total_time / num_batches (0.0 if no batches)."""
        # TODO
        raise NotImplementedError


class WriteBenchmark:
    """
    Measures a write path across batch sizes.

    Dependencies injected:
      - timer:    perf_counter()
      - write_fn: writes one batch (the thing being measured)
      - workload: a WorkloadGenerator
    """

    def __init__(self, timer: Timer, write_fn: WriteFn, workload: WorkloadGenerator):
        self.timer = timer
        self.write_fn = write_fn
        self.workload = workload

    def measure(self, batch_size: int, total_points: int) -> WriteResult:
        """
        Generate `total_points`, split them into batches of `batch_size`, and time
        writing every batch (sum the per-batch durations into total_time).

        - The last batch may be smaller than batch_size.
        - num_batches = ceil(total_points / batch_size).
        - Time each write_fn(batch) via the injected timer and accumulate.
        """
        # TODO: generate points; iterate batches; time each write_fn(batch); build WriteResult.
        raise NotImplementedError

    def sweep(self, batch_sizes: List[int], total_points: int) -> List[WriteResult]:
        """Run measure() for each batch size and return the results in order."""
        # TODO
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Fakes for deterministic tests
# ---------------------------------------------------------------------------
class FakeTimer:
    def __init__(self, times: List[float]):
        self._times = list(times)
        self._last = times[0] if times else 0.0

    def perf_counter(self) -> float:
        if self._times:
            self._last = self._times.pop(0)
        return self._last


class RecordingWriter:
    """Records every batch it 'writes' so tests can inspect calls."""
    def __init__(self):
        self.batches: List[List[Point]] = []

    def __call__(self, batch: List[Point]) -> None:
        self.batches.append(list(batch))


def test_write_benchmark():
    print("Testing Write Performance Benchmark...")

    # Test 1: workload is deterministic for a given seed
    a = WorkloadGenerator(seed=7).generate(100)
    b = WorkloadGenerator(seed=7).generate(100)
    assert a == b and len(a) == 100
    assert set(a[0].keys()) == {"measurement", "timestamp", "tags", "fields"}
    print("✓ Test 1 passed: deterministic workload")

    # Test 2: measure splits into the right number of batches
    writer = RecordingWriter()
    # 10 points, batch 4 -> 3 batches (4,4,2). Timer: 2 ticks per batch.
    timer = FakeTimer([0, 1, 1, 3, 3, 4])  # per-batch durations: 1, 2, 1
    wb = WriteBenchmark(timer, writer, WorkloadGenerator(seed=1))
    res = wb.measure(batch_size=4, total_points=10)
    assert res.num_batches == 3 and len(writer.batches) == 3
    assert [len(x) for x in writer.batches] == [4, 4, 2]
    print("✓ Test 2 passed: batching")

    # Test 3: total_time is the sum of per-batch durations
    assert res.total_time == 4  # 1 + 2 + 1
    print("✓ Test 3 passed: total_time accumulation")

    # Test 4: throughput = total_points / total_time
    assert abs(res.throughput - (10 / 4)) < 1e-9
    print("✓ Test 4 passed: throughput")

    # Test 5: mean_batch_latency = total_time / num_batches
    assert abs(res.mean_batch_latency - (4 / 3)) < 1e-9
    print("✓ Test 5 passed: mean batch latency")

    # Test 6: all generated points were written exactly once
    total_written = sum(len(x) for x in writer.batches)
    assert total_written == 10
    print("✓ Test 6 passed: all points written")

    # Test 7: sweep amortization — bigger batches -> higher throughput.
    # Model per-batch cost = fixed_overhead(1.0) regardless of size, so throughput rises.
    class ModelTimer:
        def __init__(self): self.t = 0.0
        def perf_counter(self): return self.t
    class OverheadWriter:
        def __init__(self, timer): self.timer = timer
        def __call__(self, batch): self.timer.t += 1.0  # constant cost per batch
    mt = ModelTimer()
    wb2 = WriteBenchmark(mt, OverheadWriter(mt), WorkloadGenerator(seed=2))
    results = wb2.sweep(batch_sizes=[1, 10, 100], total_points=100)
    tps = [r.throughput for r in results]
    assert tps[0] < tps[1] < tps[2], f"throughput should rise with batch size: {tps}"
    print(f"✓ Test 7 passed: amortization curve {[round(x,2) for x in tps]}")

    # Test 8: sweep returns one result per batch size, in order
    assert [r.batch_size for r in results] == [1, 10, 100]
    print("✓ Test 8 passed: sweep ordering")

    print("\n🎉 All write benchmark tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement WorkloadGenerator.generate, WriteResult properties, and
       WriteBenchmark.measure / sweep.
    2. Run: python day30_write_benchmark.py
    3. All 8 tests should pass.

    Success criteria:
    - The workload is reproducible for a fixed seed
    - measure() batches correctly (last batch may be short) and sums per-batch time
    - throughput and mean_batch_latency are derived correctly
    - sweep() shows throughput rising with batch size (amortization)

    Next steps:
    - Day 31: benchmark the READ path — indexed queries vs full scans.
    - Think about: why does throughput plateau (and eventually fall) at very large
      batches in a real system? (Hint: memory, GC, and lost parallelism.)
    """
    test_write_benchmark()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Batching Amortizes Fixed Overhead
   - Every write carries fixed costs (call overhead, index bookkeeping, durability
     intent). Batching spreads that cost over many points, so points/sec rises steeply
     with batch size before flattening.

2. Throughput vs Latency
   - Throughput (points/sec) measures aggregate capacity; per-batch latency measures
     responsiveness. Bigger batches raise throughput but also raise the latency of any
     single flush — a classic tension the curve makes visible.

3. Reproducible Workloads
   - A seeded generator means the same data every run, so throughput differences reflect
     CODE changes, not random input. This is essential for A/B comparisons.

4. Injected Write Target
   - By measuring an injected write_fn, the harness is agnostic to WHAT it writes — a
     fake in tests, your Week 1 StorageManager in the lab. The benchmark logic is tested
     deterministically without touching disk.

Connection to InfluxDB:
- InfluxDB clients batch line protocol (default flushes at thousands of points / fixed
  interval) precisely because per-request overhead dominates single-point writes. Tuning
  batch size against this curve is standard operational practice.

Trade-offs:
- Larger batches: higher throughput, more memory, higher tail latency per flush, and
  bigger data loss window on crash before flush. Real systems pick a batch size (and
  flush interval) that balances throughput against durability and latency SLOs.
"""
