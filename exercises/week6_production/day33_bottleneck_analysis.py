#!/usr/bin/env python3
"""
Day 33: Bottleneck Identification (profiling & Amdahl's law)
==========================================================

Problem: Week 5 told you HOW fast the system is; now find WHERE the time goes and what
is worth fixing. Given per-operation timings (from your Week 4 MetricsCollector), rank
the hotspots, apply the Pareto lens (which few operations dominate), and use Amdahl's
law to predict the payoff of optimizing each one — so you optimize the thing that
actually moves the needle, not the thing that's merely annoying.

Learning Objectives:
- Rank operations by their share of total time (hotspots)
- Compute cumulative share to find the Pareto "vital few"
- Apply Amdahl's law: overall speedup = 1 / ((1 - p) + p/s)
- Compute the theoretical MAX speedup from optimizing a component (s -> infinity)
- Understand why optimizing a 5% component can never help more than ~5%

Real-World Connection:
Every profiler (py-spy, perf, pprof) ranks functions by self/cumulative time. Amdahl's
law is the reason "optimize the hot path" is dogma: effort spent on anything but the
dominant cost is capped by that component's share. This is how databases decide what to
tune next.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Hotspot:
    """One operation's contribution to total runtime."""
    operation: str
    total_time: float
    share: float             # fraction of total time (0..1)
    cumulative_share: float  # running sum of shares when ranked desc


class BottleneckAnalyzer:
    """
    Analyzes per-operation timings (e.g. {op_name: total_seconds}) to rank bottlenecks
    and reason about optimization payoff. Timings are injected — in the lab they come
    from the Week 4 MetricsCollector.
    """

    def __init__(self, timings: Dict[str, float]):
        self.timings = dict(timings)

    def total(self) -> float:
        """Sum of all operation times."""
        # TODO: return sum of self.timings.values()
        return sum(self.timings.values())

    def rank(self) -> List[Hotspot]:
        """
        Return Hotspots sorted by total_time DESCENDING, each with its share of the
        total and the running cumulative share. If total is 0, all shares are 0.
        Ties broken by operation name (ascending) for determinism.
        """
        # TODO: sort items by (-time, name); compute share = time/total and a running
        #       cumulative; build Hotspot objects.
        total_time = self.total()
        ranked_hotspots = []
        cumulative_share = 0.0
        for operation, time in sorted(self.timings.items(), key=lambda x: (-x[1], x[0])):
            share = time / total_time if total_time > 0 else 0.0
            cumulative_share += share
            ranked_hotspots.append(Hotspot(operation, time, share, cumulative_share))
        return ranked_hotspots

    def top_contributors(self, threshold: float = 0.8) -> List[Hotspot]:
        """
        Return the smallest prefix of ranked hotspots whose CUMULATIVE share reaches
        `threshold` (the Pareto "vital few"). Always returns at least one hotspot when
        there is any data.
        """
        # TODO: walk rank(); collect until cumulative_share >= threshold (inclusive).
        ranked = self.rank()
        top = []
        for hotspot in ranked:
            top.append(hotspot)
            if hotspot.cumulative_share >= threshold:
                break
        return top

    @staticmethod
    def amdahl_speedup(fraction: float, component_speedup: float) -> float:
        """
        Overall speedup when a component that is `fraction` of total time is made
        `component_speedup`x faster:
            overall = 1 / ((1 - fraction) + fraction / component_speedup)
        """
        # TODO: implement the formula (assume component_speedup > 0)
        return 1 / ((1 - fraction) + fraction / component_speedup)

    @staticmethod
    def max_speedup(fraction: float) -> float:
        """
        Theoretical ceiling as component_speedup -> infinity: 1 / (1 - fraction).
        (fraction == 1 -> infinite; return float('inf').)
        """
        # TODO
        return float('inf') if fraction == 1 else 1 / (1 - fraction)


def test_bottleneck_analysis():
    print("Testing Bottleneck Identification...")

    timings = {"read": 60.0, "filter": 30.0, "aggregate": 10.0}  # total 100
    ba = BottleneckAnalyzer(timings)

    # Test 1: total
    assert ba.total() == 100.0
    print("✓ Test 1 passed: total")

    # Test 2: rank order + shares
    ranked = ba.rank()
    assert [h.operation for h in ranked] == ["read", "filter", "aggregate"]
    assert abs(ranked[0].share - 0.6) < 1e-9
    assert abs(ranked[1].share - 0.3) < 1e-9
    print("✓ Test 2 passed: ranking + shares")

    # Test 3: cumulative shares
    assert abs(ranked[0].cumulative_share - 0.6) < 1e-9
    assert abs(ranked[1].cumulative_share - 0.9) < 1e-9
    assert abs(ranked[2].cumulative_share - 1.0) < 1e-9
    print("✓ Test 3 passed: cumulative share")

    # Test 4: Pareto top contributors at 80%
    top = ba.top_contributors(0.8)
    assert [h.operation for h in top] == ["read", "filter"]  # 0.6 then 0.9 >= 0.8
    print("✓ Test 4 passed: top contributors (Pareto)")

    # Test 5: Amdahl — optimize 'read' (60%) by 2x
    # overall = 1 / (0.4 + 0.6/2) = 1 / 0.7 = 1.4286
    sp = BottleneckAnalyzer.amdahl_speedup(0.6, 2.0)
    assert abs(sp - (1 / 0.7)) < 1e-9
    print(f"✓ Test 5 passed: amdahl_speedup = {sp:.3f}x")

    # Test 6: optimizing a small component is capped
    # max speedup from a 10% component is only 1/0.9 = 1.111x, even infinitely fast
    assert abs(BottleneckAnalyzer.max_speedup(0.1) - (1 / 0.9)) < 1e-9
    assert BottleneckAnalyzer.amdahl_speedup(0.1, 1e9) < 1.12
    print("✓ Test 6 passed: small component capped")

    # Test 7: fraction == 1 -> infinite ceiling
    assert BottleneckAnalyzer.max_speedup(1.0) == float("inf")
    print("✓ Test 7 passed: full-fraction ceiling")

    # Test 8: zero-total is handled (no division by zero)
    zero = BottleneckAnalyzer({"a": 0.0, "b": 0.0})
    assert zero.total() == 0.0
    assert all(h.share == 0.0 for h in zero.rank())
    print("✓ Test 8 passed: zero-total handled")

    print("\n🎉 All bottleneck analysis tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement BottleneckAnalyzer (total, rank, top_contributors, amdahl_speedup,
       max_speedup).
    2. Run: python day33_bottleneck_analysis.py
    3. All 8 tests should pass.

    Success criteria:
    - rank() orders by time desc with correct share + cumulative share
    - top_contributors() returns the Pareto vital few
    - Amdahl's law and the max-speedup ceiling are correct
    - zero-total input doesn't divide by zero

    Next steps:
    - Day 34: actually optimize the #1 hotspot and PROVE the improvement.
    - Think about: if 'read' is 60% of time, why is 2x on it worth more than 10x on a
      10% component?
    """
    test_bottleneck_analysis()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Profile Before Optimizing
   - Intuition about "what's slow" is usually wrong. Ranking measured per-operation time
     replaces guessing with evidence — the first rule of performance work.

2. Pareto / Cumulative Share
   - A few operations usually dominate total time. Cumulative share finds the "vital
     few" that, fixed, capture most of the win — so you don't scatter effort.

3. Amdahl's Law
   - overall = 1/((1-p) + p/s). The un-optimized fraction (1-p) is a hard floor: no
     matter how fast you make a component, you can't beat 1/(1-p) overall. This is why
     the DOMINANT cost is the only one worth deep optimization.

4. Effort Allocation
   - Combine ranking + Amdahl: optimize the biggest p first, and stop when the predicted
     overall gain no longer justifies the effort. Optimization has diminishing returns by
     construction.

Connection to InfluxDB:
- Production TSDB tuning is exactly this loop: profile a workload, find the dominant cost
  (often compaction, cardinality, or a hot query shape), optimize it, re-measure. Amdahl
  is why "the write path is 80% of time" decides where the team's next quarter goes.

Trade-offs:
- Profiling adds overhead and its own noise; sampling profilers trade precision for low
  overhead. And Amdahl assumes a fixed workload — changing the workload (e.g. better
  batching) can beat any single-component optimization.
"""
