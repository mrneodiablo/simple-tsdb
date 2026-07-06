#!/usr/bin/env python3
"""
Day 17: Percentile Calculations (p50 / p95 / p99, exact vs approximate)
======================================================================

Problem: Latency SLOs live and die by percentiles — "p99 < 200ms". The mean hides
tail behavior; percentiles expose it. But an exact percentile needs all the data
sorted (O(n) memory), which doesn't scale. Implement BOTH an exact percentile
(sorting + interpolation) and a bounded-memory *approximate* one (a fixed-size
histogram), then measure the approximation error.

Learning Objectives:
- Compute an exact percentile with linear interpolation between ranks
- Understand percentile rank: p = fraction of data <= the returned value
- Build a fixed-bucket histogram that estimates percentiles in O(buckets) memory
- Quantify the accuracy vs memory trade-off
- See why databases ship approximate quantiles for high-cardinality data

Real-World Connection:
InfluxDB's `quantile(method: "exact_mean" | "estimate_tdigest")` is exactly this
choice: exact (sort everything) vs t-digest (bounded memory, approximate). Prometheus
histograms and Grafana's p99 panels use the bucketed approach you build here.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Optional


def exact_percentile(values: List[float], p: float) -> Optional[float]:
    """
    Exact percentile using linear interpolation between closest ranks (the
    "linear" / numpy-default method).

    Steps:
      - if values is empty -> None
      - sort a copy of the values
      - rank = p/100 * (n - 1)   (0-based fractional index)
      - lo = floor(rank), hi = ceil(rank), frac = rank - lo
      - return sorted[lo] + frac * (sorted[hi] - sorted[lo])

    p is in [0, 100]. p=50 -> median, p=0 -> min, p=100 -> max.
    """
    # TODO: implement the interpolation described above
    raise NotImplementedError


@dataclass
class HistogramQuantile:
    """
    Approximate quantiles in bounded memory using fixed-width buckets over a known
    value range [lo, hi]. Each bucket counts how many values fell into it; the
    percentile is found by walking cumulative counts until the target rank.

    Memory is O(num_buckets), independent of how many values you add.
    """
    lo: float
    hi: float
    num_buckets: int = 100
    _counts: List[int] = field(default_factory=list)
    _total: int = 0

    def __post_init__(self):
        if self.hi <= self.lo:
            raise ValueError("hi must be > lo")
        if self.num_buckets < 1:
            raise ValueError("num_buckets must be >= 1")
        self._counts = [0] * self.num_buckets

    def _bucket_index(self, value: float) -> int:
        """
        Map a value to a bucket index in [0, num_buckets-1], clamping out-of-range
        values into the first/last bucket.
        """
        # TODO: width = (hi - lo) / num_buckets; idx = int((value - lo) / width);
        #       clamp idx into [0, num_buckets-1]
        raise NotImplementedError

    def add(self, value: float) -> None:
        """Record one value into its bucket."""
        # TODO: increment the right bucket and self._total
        raise NotImplementedError

    def add_all(self, values: List[float]) -> None:
        for v in values:
            self.add(v)

    def percentile(self, p: float) -> Optional[float]:
        """
        Estimate the p-th percentile. Return None if empty.

        Walk buckets accumulating counts until the cumulative count reaches
        target_rank = ceil(p/100 * total). Return the CENTER of that bucket:
            center = lo + (bucket_index + 0.5) * width
        (Using the center keeps error within half a bucket width.)
        """
        # TODO: handle empty; compute target_rank; scan cumulative counts; return center
        raise NotImplementedError


def test_percentiles():
    print("Testing Percentile Calculations...")

    # Test 1: exact percentile basics on 1..100
    data = list(range(1, 101))  # 1..100
    assert exact_percentile(data, 0) == 1
    assert exact_percentile(data, 100) == 100
    # median of 1..100 via linear interp = 50.5
    assert abs(exact_percentile(data, 50) - 50.5) < 1e-9
    print("✓ Test 1 passed: exact min/max/median")

    # Test 2: exact interpolation between elements
    # [10, 20, 30, 40]; p=50 -> rank 1.5 -> 25
    assert exact_percentile([10, 20, 30, 40], 50) == 25
    print("✓ Test 2 passed: exact interpolation")

    # Test 3: empty input -> None
    assert exact_percentile([], 95) is None
    print("✓ Test 3 passed: empty -> None")

    # Test 4: p95 / p99 pick the tail
    p95 = exact_percentile(data, 95)
    p99 = exact_percentile(data, 99)
    assert 94 <= p95 <= 96 and 98 <= p99 <= 100
    assert p99 >= p95
    print(f"✓ Test 4 passed: p95={p95}, p99={p99}")

    # Test 5: histogram bucket mapping + clamping
    h = HistogramQuantile(lo=0, hi=100, num_buckets=100)
    assert h._bucket_index(-5) == 0        # below range clamps to 0
    assert h._bucket_index(105) == 99      # above range clamps to last
    assert h._bucket_index(50) == 50
    print("✓ Test 5 passed: bucket index + clamping")

    # Test 6: histogram approximates exact within one bucket width
    h = HistogramQuantile(lo=0, hi=1000, num_buckets=200)  # bucket width = 5
    import random
    random.seed(42)
    sample = [random.uniform(0, 1000) for _ in range(10000)]
    h.add_all(sample)
    approx_p95 = h.percentile(95)
    true_p95 = exact_percentile(sample, 95)
    assert abs(approx_p95 - true_p95) <= 10, f"approx {approx_p95} vs true {true_p95}"
    print(f"✓ Test 6 passed: approx p95={approx_p95:.1f} vs exact {true_p95:.1f}")

    # Test 7: histogram memory is bounded (num_buckets, not num values)
    assert len(h._counts) == 200 and h._total == 10000
    print("✓ Test 7 passed: bounded memory (200 buckets, 10k values)")

    # Test 8: empty histogram -> None
    assert HistogramQuantile(0, 10, 10).percentile(50) is None
    print("✓ Test 8 passed: empty histogram -> None")

    print("\n🎉 All percentile tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement exact_percentile and the HistogramQuantile methods
       (_bucket_index, add, percentile).
    2. Run: python day17_percentiles.py
    3. All 8 tests should pass.

    Success criteria:
    - exact_percentile interpolates correctly and handles p=0/100 and empty input
    - the histogram uses O(num_buckets) memory and approximates within a bucket width
    - both agree closely on a large random sample

    Next steps:
    - Day 18: apply these aggregates per time window (aggregateWindow).
    - Think about: how would you pick lo/hi without knowing the data first?
      (Hint: that's the problem t-digest / HDR-histogram solve.)
    """
    test_percentiles()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Percentile Rank & Interpolation
   - The p-th percentile is the value below which p% of data falls. With finite data
     the exact rank is usually fractional, so we interpolate between the two nearest
     sorted values. Different tools use slightly different rank conventions; we use
     the common linear method (p/100*(n-1)).

2. Exact vs Approximate
   - Exact needs the whole sorted dataset (O(n) memory, O(n log n) time). Approximate
     methods trade a little accuracy for bounded memory — essential when you have
     millions of points per series or must merge results across shards.

3. Fixed-Bucket Histogram
   - Pre-decide a range and bucket width; each value increments a counter. A
     percentile is a cumulative-count walk. Error is bounded by the bucket width, so
     resolution is a tunable memory knob. Weakness: you must know the range up front,
     and skewed data wastes buckets.

4. Mergeability
   - Histograms (and t-digests) add: partial results from many files/shards merge by
     summing bucket counts. Exact percentiles do not merge — you'd have to re-sort the
     union. This is why distributed systems prefer approximate quantiles.

Connection to InfluxDB:
- `quantile()` offers exact vs t-digest estimation; Prometheus `histogram_quantile()`
  over bucketed counters is the same cumulative-count walk you implemented.

Trade-offs:
- More buckets -> less error, more memory. Exact -> perfect but unbounded. Real
  systems default to approximate for the tail (p95/p99) where the cost of exactness
  is highest and a few percent of error is acceptable.
"""
