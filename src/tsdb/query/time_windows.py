#!/usr/bin/env python3

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
    if not s:
        raise ValueError("empty duration string")
    unit_multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    num_part = s[:-1]
    unit_part = s[-1]
    if unit_part not in unit_multipliers:
        raise ValueError(f"unknown duration unit: {unit_part}")
    try:
        num = float(num_part)
    except ValueError:
        raise ValueError(f"invalid duration number: {num_part}")
    return num * unit_multipliers[unit_part]


def window_start(timestamp: float, interval: float, origin: float = 0.0) -> float:
    """
    Return the start (left edge) of the window that `timestamp` falls into, aligned
    to `origin` (default: the Unix epoch, so 5m windows start at :00, :05, ...).

        offset = timestamp - origin
        bucket = int(offset // interval)
        return origin + bucket * interval

    Windows are half-open: [start, start + interval).
    """
    # TODO: implement the floor-to-boundary alignment above
    if interval <= 0:
        raise ValueError("interval must be positive")
    offset = timestamp - origin
    bucket = int(offset // interval)
    return origin + bucket * interval


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
        if not points:
            return []
        aggregators: Dict[float, Any] = {}
        counts: Dict[float, int] = {}
        for point in points:
            ts = point["timestamp"]
            w = window_start(ts, interval, origin)
            if w not in aggregators:
                aggregators[w] = self.agg_factory()
                counts[w] = 0
            aggregators[w].update(point["fields"].get(self.field_key))
            counts[w] += 1

        if fill_empty and aggregators:
            min_w = min(aggregators.keys())
            max_w = max(aggregators.keys())
            w = min_w
            while w <= max_w:
                if w not in aggregators:
                    aggregators[w] = None
                    counts[w] = 0
                w += interval

        results = []
        for w in sorted(aggregators.keys()):
            agg = aggregators[w]
            count = counts[w]
            value = agg.result() if agg is not None else None
            results.append(WindowResult(start=w, end=w+interval, value=value, count=count))
        return results


def _pt(ts: float, value: float) -> Dict[str, Any]:
    return {"measurement": "cpu", "timestamp": ts, "tags": {}, "fields": {"value": value}}

