#!/usr/bin/env python3
"""
Day 31: Query Performance Analysis (indexed vs full scan)
========================================================

Problem: The whole point of Week 2's indexes was to avoid reading data you don't need.
Now PROVE it: benchmark representative query shapes — a point lookup, a time-range
scan, an aggregation, a group-by — each run two ways: using the index vs a brute-force
full scan. The speedup (scan_time / indexed_time) quantifies exactly what the index
buys you, per query shape.

Learning Objectives:
- Define a small suite of representative query scenarios
- Measure the same query two ways (indexed vs scan) and compare
- Compute speedup as a ratio and reason about when it's large vs small
- Understand that selective queries benefit most from indexes
- Keep both query functions injected so the comparison is deterministic in tests

Real-World Connection:
This mirrors how TSDB performance is characterized: run a fixed query set (e.g. TSBS's
"single-groupby", "high-cpu", "double-groupby") and report latency per query type.
InfluxDB's TSI shines on selective tag lookups and loses its edge on full-measurement
scans — exactly the pattern this benchmark reveals.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Protocol, Tuple


class Timer(Protocol):
    def perf_counter(self) -> float: ...


class QueryScenario(str, Enum):
    POINT = "point"              # single series / tag equality
    RANGE = "range"             # time-range scan
    AGGREGATION = "aggregation"  # mean/sum over a window
    GROUP_BY = "group_by"       # per-tag aggregation


@dataclass
class ScenarioComparison:
    scenario: str
    indexed_mean: float
    scan_mean: float

    @property
    def speedup(self) -> float:
        """scan_mean / indexed_mean (how many x faster indexed is; 0.0 if indexed is 0)."""
        # TODO
        if self.indexed_mean == 0:
            return 0.0
        return self.scan_mean / self.indexed_mean
        

    @property
    def indexed_wins(self) -> bool:
        """True if the indexed path is strictly faster than the scan."""
        # TODO
        return self.indexed_mean < self.scan_mean


class QueryBenchmark:
    """
    Times two implementations of the same query and compares them.

    Dependency injected:
      - timer: perf_counter()
    """

    def __init__(self, timer: Timer):
        self.timer = timer

    def _mean_time(self, fn: Callable[[], object], iterations: int) -> float:
        """Run fn `iterations` times, timing each with the injected timer; return mean duration."""
        # TODO: time each call (start/end via self.timer), return sum/iterations.
        total_time = 0.0
        for _ in range(iterations):
            start = self.timer.perf_counter()
            fn()
            end = self.timer.perf_counter()
            total_time += (end - start)
        return total_time / iterations if iterations > 0 else 0.0

    def compare(self, scenario: str, indexed_fn: Callable[[], object],
                scan_fn: Callable[[], object], iterations: int = 5) -> ScenarioComparison:
        """
        Measure indexed_fn and scan_fn `iterations` times each and return a
        ScenarioComparison of their mean latencies.
        """
        # TODO: compute both means via _mean_time and build ScenarioComparison.
        indexed_mean = self._mean_time(indexed_fn, iterations)
        scan_mean = self._mean_time(scan_fn, iterations)
        return ScenarioComparison(scenario=scenario, indexed_mean=indexed_mean, scan_mean=scan_mean)

    def run_suite(self, scenarios: Dict[str, Tuple[Callable[[], object], Callable[[], object]]],
                  iterations: int = 5) -> Dict[str, ScenarioComparison]:
        """
        Run compare() for each named scenario. `scenarios` maps name -> (indexed_fn, scan_fn).
        Return name -> ScenarioComparison.
        """
        # TODO
        results = {}
        for name, (indexed_fn, scan_fn) in scenarios.items():
            results[name] = self.compare(name, indexed_fn, scan_fn, iterations=iterations)
        return results


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


def test_query_benchmark():
    print("Testing Query Performance Analysis...")

    # Test 1: _mean_time averages measured durations.
    # Timer ticks: (0,2),(2,6),(6,9) -> durations 2,4,3 -> mean 3
    qb = QueryBenchmark(FakeTimer([0, 2, 2, 6, 6, 9]))
    m = qb._mean_time(lambda: None, iterations=3)
    assert abs(m - 3.0) < 1e-9
    print("✓ Test 1 passed: _mean_time")

    # Test 2: compare builds means for both paths.
    # indexed durations: 1,1 (mean 1); scan durations: 10,10 (mean 10)
    qb = QueryBenchmark(FakeTimer([0, 1, 1, 2, 2, 12, 12, 22]))
    cmp = qb.compare("point", indexed_fn=lambda: None, scan_fn=lambda: None, iterations=2)
    assert abs(cmp.indexed_mean - 1.0) < 1e-9 and abs(cmp.scan_mean - 10.0) < 1e-9
    print("✓ Test 2 passed: compare means")

    # Test 3: speedup ratio
    assert abs(cmp.speedup - 10.0) < 1e-9 and cmp.indexed_wins is True
    print("✓ Test 3 passed: speedup + indexed_wins")

    # Test 4: a scenario where the index does NOT help (full-measurement scan)
    # indexed 5,5 (mean 5); scan 5,5 (mean 5) -> speedup 1, no win
    qb = QueryBenchmark(FakeTimer([0, 5, 5, 10, 10, 15, 15, 20]))
    cmp2 = qb.compare("range", lambda: None, lambda: None, iterations=2)
    assert abs(cmp2.speedup - 1.0) < 1e-9 and cmp2.indexed_wins is False
    print("✓ Test 4 passed: no-win scenario")

    # Test 5: run_suite over multiple scenarios (FakeTimer scripted for 2 scenarios
    # x 2 fns x 1 iteration). scenario A: indexed 1, scan 4; scenario B: indexed 2, scan 2
    qb = QueryBenchmark(FakeTimer([0, 1, 1, 5, 5, 7, 7, 9]))
    suite = qb.run_suite({
        "A": (lambda: None, lambda: None),
        "B": (lambda: None, lambda: None),
    }, iterations=1)
    assert set(suite.keys()) == {"A", "B"}
    assert abs(suite["A"].speedup - 4.0) < 1e-9
    assert abs(suite["B"].speedup - 1.0) < 1e-9
    print("✓ Test 5 passed: run_suite")

    # Test 6: both query functions are actually invoked
    calls = {"idx": 0, "scan": 0}
    qb = QueryBenchmark(FakeTimer([0, 1, 1, 2, 2, 3, 3, 4]))
    qb.compare("agg",
               indexed_fn=lambda: calls.__setitem__("idx", calls["idx"] + 1),
               scan_fn=lambda: calls.__setitem__("scan", calls["scan"] + 1),
               iterations=2)
    assert calls == {"idx": 2, "scan": 2}
    print("✓ Test 6 passed: functions invoked")

    # Test 7: indexed_wins False when equal, True when faster
    assert ScenarioComparison("x", 2.0, 2.0).indexed_wins is False
    assert ScenarioComparison("x", 1.0, 3.0).indexed_wins is True
    print("✓ Test 7 passed: indexed_wins semantics")

    # Test 8: speedup guards divide-by-zero
    assert ScenarioComparison("x", 0.0, 5.0).speedup == 0.0
    print("✓ Test 8 passed: divide-by-zero guarded")

    print("\n🎉 All query benchmark tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement ScenarioComparison.speedup / indexed_wins and QueryBenchmark
       (_mean_time, compare, run_suite).
    2. Run: python day31_query_benchmark.py
    3. All 8 tests should pass.

    Success criteria:
    - _mean_time and compare produce correct mean latencies deterministically
    - speedup = scan/indexed, guarded against divide-by-zero
    - run_suite handles a dict of scenarios
    - the "no-win" case (full scan) correctly shows speedup ~1

    Next steps:
    - Day 32: step back from numbers to architecture — trade-offs vs InfluxDB.
    - Think about: which query shape gives the biggest index speedup, and why?
      (Hint: selectivity — how much data the index lets you skip.)
    """
    test_query_benchmark()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Representative Query Suite
   - You can't benchmark "queries" in general — you benchmark SHAPES: point lookup,
     range scan, aggregation, group-by. Each stresses a different part of the engine, so
     each gets its own number.

2. Indexed vs Scan Baseline
   - Running the same query both ways isolates the index's contribution. The full scan is
     the honest baseline: if the indexed path isn't faster, the index isn't earning its
     memory for that query shape.

3. Speedup and Selectivity
   - Speedup tracks selectivity: a tag lookup that touches 0.1% of series can be 100x+
     faster; a query that must read the whole measurement gets ~1x because there's
     nothing to skip. The benchmark makes this concrete.

4. Deterministic Comparison
   - Injecting the timer (and both query fns) means tests assert exact speedups without
     real timing. In the lab you swap in the real Week 2 indexed reader and a brute-force
     scan over the same data.

Connection to InfluxDB:
- TSBS and InfluxDB's own benchmarks report latency per query type. TSI accelerates
  selective tag/series lookups dramatically but offers little for full scans — the same
  selectivity-driven pattern your speedups show.

Trade-offs:
- Indexes cost memory and write-time maintenance to save read time. They pay off for
  selective, frequent queries and are dead weight for rare full scans. Benchmarking per
  shape tells you which indexes are worth keeping.
"""
