#!/usr/bin/env python3

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
    if not values:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    rank = p / 100 * (n - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    frac = rank - lo
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


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
        width = (self.hi - self.lo) / self.num_buckets
        idx = int((value - self.lo) / width)
        return max(0, min(self.num_buckets - 1, idx))

    def add(self, value: float) -> None:
        """Record one value into its bucket."""
        # TODO: increment the right bucket and self._total
        idx = self._bucket_index(value)
        self._counts[idx] += 1
        self._total += 1

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
        if self._total == 0:
            return None
        target_rank = math.ceil(p / 100 * self._total)
        cumulative = 0
        for i, count in enumerate(self._counts):
            cumulative += count
            if cumulative >= target_rank:
                width = (self.hi - self.lo) / self.num_buckets
                return self.lo + (i + 0.5) * width
        # Should not reach here, but return the last bucket center as a fallback
        width = (self.hi - self.lo) / self.num_buckets
        return self.lo + (self.num_buckets - 0.5) * width

