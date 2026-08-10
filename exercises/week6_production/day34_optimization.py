#!/usr/bin/env python3
"""
Day 34: Production Optimization (before/after, with a correctness guard)
=======================================================================

Problem: An optimization you can't prove is a rumor — and one that changes the answer
is a bug, not a speedup. The professional loop is: keep the baseline, write the
optimized version, verify it produces IDENTICAL output on the same inputs, THEN measure
the improvement. "Faster but wrong" must fail loudly. Build the harness that enforces
both halves.

Learning Objectives:
- Measure a baseline and an optimized implementation on identical inputs
- Guard correctness: optimized(input) must equal baseline(input) for every input
- Report speedup only when correctness holds (else flag a regression)
- Separate the measurement harness from the code being measured (inject both)
- Make timing deterministic in tests with an injected clock

Real-World Connection:
This is how databases ship performance PRs: a benchmark shows the win, a test suite
proves unchanged results. InfluxDB's TSM/compaction changes always pair a benchmark
with correctness tests — a faster engine that returns wrong data is worthless.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, List, Protocol


class Timer(Protocol):
    def perf_counter(self) -> float: ...


@dataclass
class OptimizationResult:
    name: str
    baseline_time: float
    optimized_time: float
    correct: bool

    @property
    def speedup(self) -> float:
        """baseline_time / optimized_time (0.0 if optimized_time == 0)."""
        # TODO
        raise NotImplementedError

    @property
    def improved(self) -> bool:
        """True only if correctness holds AND the optimized version is faster."""
        # TODO: correct and optimized_time < baseline_time
        raise NotImplementedError


class Optimizer:
    """
    Verifies + measures an optimization.

    Dependency injected:
      - timer: perf_counter()
    """

    def __init__(self, timer: Timer):
        self.timer = timer

    @staticmethod
    def check_correctness(baseline_fn: Callable[[Any], Any],
                          optimized_fn: Callable[[Any], Any],
                          inputs: List[Any]) -> bool:
        """True iff optimized_fn(inp) == baseline_fn(inp) for every input."""
        # TODO: return all(baseline_fn(i) == optimized_fn(i) for i in inputs)
        raise NotImplementedError

    def measure_total(self, fn: Callable[[Any], Any], inputs: List[Any], iterations: int) -> float:
        """
        Total time to run `fn` over ALL inputs, repeated `iterations` times. Time each
        full pass (one perf_counter before the inner loop, one after) and sum the passes.
        """
        # TODO: for each iteration, time a pass over all inputs; accumulate and return total.
        raise NotImplementedError

    def optimize(self, name: str, baseline_fn: Callable[[Any], Any],
                 optimized_fn: Callable[[Any], Any], inputs: List[Any],
                 iterations: int = 1) -> OptimizationResult:
        """
        Run the full loop:
          1. correct = check_correctness(...)
          2. baseline_time = measure_total(baseline_fn, ...)
          3. optimized_time = measure_total(optimized_fn, ...)
          4. return OptimizationResult(name, baseline_time, optimized_time, correct)
        (Always measure both, even if incorrect — the numbers are still informative.)
        """
        # TODO: implement the 4 steps above.
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


def test_optimization():
    print("Testing Production Optimization...")

    inputs = [[1, 2, 3], [4, 5], [10]]

    def baseline_sum(xs):
        total = 0
        for x in xs:
            total += x
        return total

    def optimized_sum(xs):
        return sum(xs)  # same result, faster path

    # Test 1: correctness check passes for an equivalent optimization
    assert Optimizer.check_correctness(baseline_sum, optimized_sum, inputs) is True
    print("✓ Test 1 passed: correctness holds")

    # Test 2: measure_total sums timed passes.
    # iterations=1 -> one pass: timer (0 -> 10) => 10
    t = FakeTimer([0, 10])
    assert Optimizer(t).measure_total(baseline_sum, inputs, iterations=1) == 10
    print("✓ Test 2 passed: measure_total")

    # Test 3: full optimize — baseline pass 10s, optimized pass 1s
    t = FakeTimer([0, 10, 10, 11])  # baseline 0->10, optimized 10->11
    res = Optimizer(t).optimize("sum", baseline_sum, optimized_sum, inputs)
    assert res.correct is True
    assert res.baseline_time == 10 and res.optimized_time == 1
    print("✓ Test 3 passed: optimize measures both")

    # Test 4: speedup + improved
    assert res.speedup == 10.0 and res.improved is True
    print("✓ Test 4 passed: speedup + improved")

    # Test 5: a WRONG optimization is flagged, never counts as improved
    def buggy_sum(xs):
        return sum(xs) + 1  # faster-but-wrong

    assert Optimizer.check_correctness(baseline_sum, buggy_sum, inputs) is False
    t = FakeTimer([0, 10, 10, 11])  # even though "faster"
    bad = Optimizer(t).optimize("buggy", baseline_sum, buggy_sum, inputs)
    assert bad.correct is False and bad.improved is False
    print("✓ Test 5 passed: faster-but-wrong rejected")

    # Test 6: a correct-but-slower change is not an improvement
    t = FakeTimer([0, 5, 5, 20])  # baseline 5, optimized 15
    slower = Optimizer(t).optimize("slower", baseline_sum, optimized_sum, inputs)
    assert slower.correct is True and slower.improved is False
    assert slower.speedup < 1.0
    print("✓ Test 6 passed: correct-but-slower not improved")

    # Test 7: iterations repeat the pass (2 passes accumulate)
    t = FakeTimer([0, 3, 3, 7])  # pass1=3, pass2=4 -> total 7
    total = Optimizer(t).measure_total(baseline_sum, inputs, iterations=2)
    assert total == 7
    print("✓ Test 7 passed: iterations accumulate")

    # Test 8: speedup guards divide-by-zero
    assert OptimizationResult("x", 5.0, 0.0, True).speedup == 0.0
    print("✓ Test 8 passed: divide-by-zero guarded")

    print("\n🎉 All optimization tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement OptimizationResult.speedup/improved and Optimizer
       (check_correctness, measure_total, optimize).
    2. Run: python day34_optimization.py
    3. All 8 tests should pass.

    Success criteria:
    - Correctness is verified on identical inputs before any speedup is claimed
    - optimize() measures both versions deterministically via the injected timer
    - `improved` is True ONLY when correct AND faster
    - a faster-but-wrong change is flagged, not celebrated

    Next steps:
    - Day 35: apply what you learned to a real work system as prioritized actions.
    - Think about: why measure the WRONG version's time too? (Hint: it tells you how
      much speed you'd be trading for the bug.)
    """
    test_optimization()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Optimization Is a Loop, Not an Edit
   - baseline -> change -> verify correctness -> measure -> keep or revert. Skipping the
     verify or measure step is how "optimizations" silently break or fail to help.

2. Correctness Guard
   - The optimized code must return the SAME results as the baseline on the same inputs.
     Encoding this as a hard gate means a faster-but-wrong change can never be reported
     as an improvement — it fails.

3. Prove the Win
   - A speedup number with no baseline is meaningless. Measuring both under the same
     harness (and injected timer, for determinism) makes the improvement defensible and
     reproducible.

4. Regression Awareness
   - Tracking `improved = correct and faster` catches both regressions: wrong answers AND
     performance regressions (correct but slower). Both should block a merge.

Connection to InfluxDB:
- Performance PRs in real databases pair a benchmark (the win) with correctness tests
  (unchanged results). Compaction, encoding, and query-planner changes are all gated this
  way — speed never ships at the cost of correctness.

Trade-offs:
- Verifying correctness on every input costs time and needs representative inputs; a
  guard is only as good as its test set. And micro-optimizations that pass locally can
  still regress under real concurrency/data — which is why the lab re-measures end to end.
"""
