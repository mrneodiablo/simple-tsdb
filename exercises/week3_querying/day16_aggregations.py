#!/usr/bin/env python3
"""
Day 16: Aggregation Functions (streaming sum / count / mean / min / max)
=======================================================================

Problem: After filtering, a query usually collapses many points into one number:
"mean CPU", "max latency", "count of errors". Compute these in a single streaming
pass — O(1) memory, one point at a time — so they work on data far larger than RAM
and can later plug into time windows (Day 18) and group-by (Day 19).

Learning Objectives:
- Implement the streaming accumulator pattern: init -> update(x) -> result()
- Compute mean without storing all values (running count + sum)
- Handle null / missing / non-numeric field values gracefully
- Use a numerically stable running mean (Welford) to avoid precision loss
- Build a registry so a query can request aggregators by name

Real-World Connection:
Flux's `sum()`, `count()`, `mean()`, `min()`, `max()` are streaming reducers applied
per table. InfluxDB never materializes the whole column to average it — it folds the
stream. The Aggregator interface here is exactly that fold.
"""

from __future__ import annotations
import math
from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Dict, Callable


def is_number(x: Any) -> bool:
    """True if x is a real, finite number we can aggregate (bool excluded)."""
    # TODO: return True only for int/float (NOT bool) that is finite (not NaN/inf)
    raise NotImplementedError


class Aggregator(ABC):
    """
    Streaming aggregator. Feed values with update(); read the answer with result().
    Non-numeric / None values should be ignored by update() (null handling).
    """

    @abstractmethod
    def update(self, value: Any) -> None:
        ...

    @abstractmethod
    def result(self) -> Optional[float]:
        """Final value, or None if no valid values were seen."""
        ...

    def update_many(self, values: Iterable[Any]) -> "Aggregator":
        for v in values:
            self.update(v)
        return self


class Count(Aggregator):
    """Counts the number of NON-NULL numeric values seen."""

    def __init__(self):
        self._n = 0

    def update(self, value: Any) -> None:
        # TODO: increment only when is_number(value)
        raise NotImplementedError

    def result(self) -> Optional[float]:
        # TODO: return the count (as a number; 0 is valid, not None)
        raise NotImplementedError


class Sum(Aggregator):
    def __init__(self):
        self._sum = 0.0
        self._seen = False

    def update(self, value: Any) -> None:
        # TODO: add numeric values; remember whether any value was seen
        raise NotImplementedError

    def result(self) -> Optional[float]:
        # TODO: return the sum, or None if nothing valid was seen
        raise NotImplementedError


class Mean(Aggregator):
    """
    Numerically stable running mean (Welford's algorithm):
        n += 1
        delta = x - mean
        mean += delta / n
    """

    def __init__(self):
        self._n = 0
        self._mean = 0.0

    def update(self, value: Any) -> None:
        # TODO: for numeric values, apply the Welford update above
        raise NotImplementedError

    def result(self) -> Optional[float]:
        # TODO: return running mean, or None if n == 0
        raise NotImplementedError


class Min(Aggregator):
    def __init__(self):
        self._min: Optional[float] = None

    def update(self, value: Any) -> None:
        # TODO: track the smallest numeric value seen
        raise NotImplementedError

    def result(self) -> Optional[float]:
        # TODO
        raise NotImplementedError


class Max(Aggregator):
    def __init__(self):
        self._max: Optional[float] = None

    def update(self, value: Any) -> None:
        # TODO
        raise NotImplementedError

    def result(self) -> Optional[float]:
        # TODO
        raise NotImplementedError


# Registry: name -> factory. A query says agg="mean"; the engine builds a fresh one.
AGGREGATORS: Dict[str, Callable[[], Aggregator]] = {
    "count": Count,
    "sum": Sum,
    "mean": Mean,
    "min": Min,
    "max": Max,
}


def aggregate_field(points: List[Dict[str, Any]], field_key: str, agg: str) -> Optional[float]:
    """
    Convenience end-to-end: pull point["fields"][field_key] from each point and
    fold it through the named aggregator. Missing fields count as null.

    Raises KeyError if `agg` is not a known aggregator name.
    """
    # TODO: look up the factory in AGGREGATORS (KeyError if unknown), build an
    #       aggregator, feed each point's field value (use .get so missing -> None),
    #       and return result().
    raise NotImplementedError


def test_aggregations():
    print("Testing Aggregation Functions...")

    # Test 1: is_number screens out junk
    assert is_number(3) and is_number(2.5)
    assert not is_number(True) and not is_number("5") and not is_number(None)
    assert not is_number(float("nan")) and not is_number(float("inf"))
    print("✓ Test 1 passed: is_number")

    vals = [10, 20, 30, 40]

    # Test 2: sum / count / mean / min / max on clean data
    assert Sum().update_many(vals).result() == 100
    assert Count().update_many(vals).result() == 4
    assert Mean().update_many(vals).result() == 25
    assert Min().update_many(vals).result() == 10
    assert Max().update_many(vals).result() == 40
    print("✓ Test 2 passed: basic aggregates")

    # Test 3: null handling — None and non-numeric ignored
    dirty = [10, None, "oops", 20, True, 30]
    assert Sum().update_many(dirty).result() == 60
    assert Count().update_many(dirty).result() == 3
    assert Mean().update_many(dirty).result() == 20
    print("✓ Test 3 passed: null / non-numeric ignored")

    # Test 4: empty stream -> None (except count -> 0)
    assert Sum().result() is None
    assert Mean().result() is None
    assert Min().result() is None
    assert Max().result() is None
    assert Count().result() == 0
    print("✓ Test 4 passed: empty stream semantics")

    # Test 5: numerical stability of running mean on large offset values
    big = [1e9 + i for i in range(1000)]  # mean should be 1e9 + 499.5
    m = Mean().update_many(big).result()
    assert abs(m - (1e9 + 499.5)) < 1e-3, f"mean drifted: {m}"
    print("✓ Test 5 passed: stable running mean")

    # Test 6: end-to-end aggregate_field over point dicts
    points = [
        {"fields": {"value": 5.0}},
        {"fields": {"value": 15.0}},
        {"fields": {}},            # missing -> null
        {"fields": {"value": 25.0}},
    ]
    assert aggregate_field(points, "value", "mean") == 15.0
    assert aggregate_field(points, "value", "count") == 3
    assert aggregate_field(points, "value", "max") == 25.0
    print("✓ Test 6 passed: aggregate_field over points")

    # Test 7: unknown aggregator name raises
    try:
        aggregate_field(points, "value", "median")
        assert False, "expected KeyError for unknown aggregator"
    except KeyError:
        pass
    print("✓ Test 7 passed: unknown aggregator raises KeyError")

    print("\n🎉 All aggregation tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement is_number, every Aggregator subclass, and aggregate_field.
    2. Run: python day16_aggregations.py
    3. All 7 tests should pass.

    Success criteria:
    - Each aggregator is a single streaming pass (no storing the full list)
    - None / non-numeric / NaN / inf values are ignored
    - Empty streams return None (count returns 0)
    - Mean stays accurate on large-offset data (Welford)

    Next steps:
    - Day 17: percentiles — the one aggregate that can't be done in O(1) memory exactly.
    - Think about: why does count return 0 on empty input while sum returns None?
    """
    test_aggregations()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Streaming Reducers (folds)
   - init -> update(x) repeatedly -> result(). Constant memory regardless of input
     size. Composable: the same aggregator drives a whole column, one window, or one
     group.

2. Null Handling
   - Real telemetry has gaps and garbage. Aggregators must skip None / non-numeric
     values rather than crash or poison the result. "count" counts what it actually
     saw; "sum"/"mean" ignore the rest.

3. Numerical Stability (Welford)
   - Naive mean = sum/n loses precision when values are large and n is big. Welford's
     running mean updates by delta/n and stays accurate; it also extends naturally to
     variance/stddev (foundation for later stats).

4. Empty-Input Semantics
   - sum/mean/min/max of nothing is undefined -> None. count of nothing is 0. Getting
     these edge cases right matters once windows can be empty (Day 18).

Connection to InfluxDB:
- Flux aggregate functions are streaming table reducers; `mean()` folds `_value`
  without materializing the column, exactly like Mean here.

Trade-offs:
- Streaming is memory-cheap and parallelizable (partial aggregates can be merged),
  but not every aggregate is streamable in O(1): percentiles/median need more state,
  which is why Day 17 exists.
"""
