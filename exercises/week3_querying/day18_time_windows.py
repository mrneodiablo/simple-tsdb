#!/usr/bin/env python3
"""
Day 18: Time Window Operations (aggregateWindow)
================================================

Problem: Dashboards don't plot raw points — they plot "mean CPU per 5 minutes".
That means bucketing points into fixed time intervals and aggregating each bucket.
The subtle parts are *alignment* (windows snap to clean boundaries like :00, :05,
not to the first data point) and *empty windows* (a gap should still produce a
bucket, or be explicitly absent). Build windowing on top of Day 16's aggregators.

Learning Objectives:
- Assign a timestamp to its window via floor division on the interval
- Align windows to an epoch so boundaries are stable across queries
- Aggregate each window with a streaming aggregator (reuse Day 16)
- Parse human durations ("5m", "1h", "30s") into seconds
- Decide how to handle empty windows (skip vs emit)

Real-World Connection:
Flux's `aggregateWindow(every: 5m, fn: mean)` does exactly this: it derives window
boundaries aligned to the Unix epoch, buckets rows, and reduces each bucket. Grafana's
"$__interval" and downsampling tasks are the same operation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


# Reuse Day 16's aggregator registry if available; otherwise a tiny local fallback
# keeps this file runnable standalone (dependency injection via `agg_factory`).
def _mean_factory():
    class _Mean:
        def __init__(self):
            self.n = 0
            self.mean = 0.0
        def update(self, v):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                self.n += 1
                self.mean += (v - self.mean) / self.n
        def result(self):
            return self.mean if self.n else None
    return _Mean()


def parse_duration(s: str) -> float:
    """
    Parse a duration string into seconds. Supported suffixes: s, m, h, d.
    Examples: "30s" -> 30, "5m" -> 300, "1h" -> 3600, "2d" -> 172800.

    Raise ValueError on an empty string, bad number, or unknown suffix.
    """
    # TODO: split number and unit suffix; map s/m/h/d to multipliers; validate
    raise NotImplementedError


def window_start(timestamp: float, interval: float, origin: float = 0.0) -> float:
    """
    Return the start (left edge) of the window that `timestamp` falls into, aligned
    to `origin` (default: the Unix epoch, so 5m windows start at :00, :05, ...).

        offset = timestamp - origin
        bucket = floor(offset / interval)
        return origin + bucket * interval

    Windows are half-open: [start, start + interval).
    """
    # TODO: implement the floor-to-boundary alignment above
    raise NotImplementedError


@dataclass
class WindowResult:
    """One aggregated window. `value` is None for an empty window that was emitted."""
    start: float
    end: float
    value: Optional[float]
    count: int


class WindowAggregator:
    """
    Buckets points by time window and aggregates each with a fresh aggregator.

    Dependencies injected:
      - agg_factory: () -> aggregator (must have .update(value) and .result())
      - field_key:  which field to aggregate from each point
    """

    def __init__(self, agg_factory: Callable[[], Any] = _mean_factory, field_key: str = "value"):
        self.agg_factory = agg_factory
        self.field_key = field_key

    def aggregate(
        self,
        points: List[Dict[str, Any]],
        interval: float,
        origin: float = 0.0,
        fill_empty: bool = False,
    ) -> List[WindowResult]:
        """
        Group points into aligned windows of width `interval` and aggregate each.

        - Points need not be sorted; bucket by window_start(ts, interval, origin).
        - Return results sorted by window start.
        - If fill_empty is True, emit a WindowResult(value=None, count=0) for every
          window between the min and max observed window that received no points.
          If False, only windows that actually contain points are returned.

        Each point's value is point["fields"].get(self.field_key) (missing -> the
        aggregator's null handling applies).
        """
        # TODO:
        #   1. return [] if points is empty
        #   2. for each point: w = window_start(ts, interval, origin);
        #      keep an aggregator per w and feed the field value; track count.
        #   3. if fill_empty: iterate w from min..max in steps of interval, emitting
        #      empty windows where none exist.
        #   4. build WindowResult(start=w, end=w+interval, value=agg.result(), count)
        #      sorted by start.
        raise NotImplementedError


def _pt(ts: float, value: float) -> Dict[str, Any]:
    return {"measurement": "cpu", "timestamp": ts, "tags": {}, "fields": {"value": value}}


def test_time_windows():
    print("Testing Time Window Operations...")

    # Test 1: duration parsing
    assert parse_duration("30s") == 30
    assert parse_duration("5m") == 300
    assert parse_duration("1h") == 3600
    assert parse_duration("2d") == 172800
    print("✓ Test 1 passed: parse_duration")

    # Test 2: bad durations raise
    for bad in ["", "5", "10x", "abc", "m"]:
        try:
            parse_duration(bad)
            assert False, f"expected ValueError for {bad!r}"
        except ValueError:
            pass
    print("✓ Test 2 passed: bad durations raise ValueError")

    # Test 3: window alignment to epoch
    # interval 300s (5m). ts=1000 -> floor(1000/300)=3 -> start 900
    assert window_start(1000, 300) == 900
    assert window_start(900, 300) == 900   # left edge is inclusive
    assert window_start(1199, 300) == 900
    assert window_start(1200, 300) == 1200
    print("✓ Test 3 passed: window alignment")

    # Test 4: aggregate into windows (mean per 60s)
    wa = WindowAggregator(agg_factory=_mean_factory, field_key="value")
    points = [
        _pt(0, 10), _pt(30, 20),      # window [0,60) -> mean 15
        _pt(60, 100), _pt(90, 200),   # window [60,120) -> mean 150
        _pt(180, 5),                  # window [180,240) -> mean 5
    ]
    res = wa.aggregate(points, interval=60)
    assert [r.start for r in res] == [0, 60, 180]
    assert res[0].value == 15 and res[1].value == 150 and res[2].value == 5
    assert res[0].count == 2 and res[2].count == 1
    print("✓ Test 4 passed: per-window mean")

    # Test 5: results sorted even if input unsorted
    res2 = wa.aggregate(list(reversed(points)), interval=60)
    assert [r.start for r in res2] == [0, 60, 180]
    print("✓ Test 5 passed: unsorted input handled")

    # Test 6: fill_empty emits the gap window [120,180)
    res3 = wa.aggregate(points, interval=60, fill_empty=True)
    starts = [r.start for r in res3]
    assert starts == [0, 60, 120, 180]
    gap = next(r for r in res3 if r.start == 120)
    assert gap.value is None and gap.count == 0
    print("✓ Test 6 passed: fill_empty emits gap windows")

    # Test 7: empty input -> empty result
    assert wa.aggregate([], interval=60) == []
    print("✓ Test 7 passed: empty input")

    # Test 8: non-zero origin shifts boundaries
    # origin=15, interval=60: ts=70 -> offset 55 -> bucket 0 -> start 15
    assert window_start(70, 60, origin=15) == 15
    assert window_start(75, 60, origin=15) == 75
    print("✓ Test 8 passed: custom origin alignment")

    print("\n🎉 All time window tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement parse_duration, window_start, and WindowAggregator.aggregate.
    2. Run: python day18_time_windows.py
    3. All 8 tests should pass.

    Success criteria:
    - Windows align to the epoch/origin, not to the first data point
    - Each window aggregates via the injected aggregator (reuse Day 16!)
    - Empty windows are handled per the fill_empty flag
    - Duration parsing validates its input

    Next steps:
    - Day 19: group by tag values (windows split by time; groups split by tag).
    - Think about: why align to a fixed epoch instead of the first point's time?
    """
    test_time_windows()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Window Assignment via Floor Division
   - The window of a timestamp is floor((ts - origin)/interval). This is O(1) per
     point and needs no sorting — you bucket, then aggregate each bucket.

2. Alignment to an Epoch
   - Snapping windows to a fixed origin (the Unix epoch) means the SAME wall-clock
     boundaries every query and every series. Two dashboards over the same range line
     up; downsampled data is stable and mergeable. Aligning to "first point" would
     shift boundaries whenever data starts a second later.

3. Empty Windows
   - A gap in the data is information ("the host was down"). fill_empty lets the
     caller choose: emit null-valued windows to keep a regular time axis, or omit
     them for a compact result. Charts usually want the regular axis.

4. Reuse of Streaming Aggregators
   - A window is just a sub-stream. Injecting Day 16's aggregator factory means
     mean/sum/max/percentile all work per window with zero new code — composition
     over duplication.

Connection to InfluxDB:
- `aggregateWindow(every: 5m, fn: mean, createEmpty: true)` maps 1:1 to this:
  `every`=interval, `fn`=aggregator, `createEmpty`=fill_empty. Flux also aligns to
  the epoch by default.

Trade-offs:
- Fixed windows are simple and mergeable but can split a burst across a boundary.
  Sliding/overlapping windows capture bursts better at higher cost — not needed here.
"""
