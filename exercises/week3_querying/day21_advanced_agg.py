#!/usr/bin/env python3
"""
Day 21: Advanced Aggregations (rate, derivative, counter resets)
================================================================

Problem: Monitoring lives on *change over time*, not raw values. Counters only ever
go up (total requests, bytes sent); what you actually want is the RATE ("requests per
second"). Gauges need the DERIVATIVE ("how fast is temperature rising"). The hard part
is counter RESETS: a process restart drops the counter to 0, and a naive difference
would report a huge negative rate. Implement rate/derivative with reset handling.

Learning Objectives:
- Compute a derivative: (Δvalue / Δtime) between consecutive points
- Compute a rate: per-second change of a monotonic counter
- Detect and correct counter resets (value drops => assume restart)
- Normalize rates to a unit interval (per second) regardless of sample spacing
- Understand why counters, not gauges, need reset handling

Real-World Connection:
Prometheus `rate()`/`increase()` and Flux `derivative(nonNegative: true)` do exactly
this: pairwise differences over time with counter-reset correction. Getting resets
wrong is one of the most common monitoring bugs (phantom negative spikes).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Sample:
    """A (timestamp, value) reading. Points are assumed sorted by ts for these ops."""
    timestamp: float
    value: float


def derivative(samples: List[Sample]) -> List[Sample]:
    """
    Instantaneous derivative between consecutive samples: for each adjacent pair
    (a, b), emit Sample(timestamp=b.timestamp, value=(b.value - a.value)/(b.timestamp
    - a.timestamp)). The result has len(samples)-1 entries (the first point has no
    predecessor).

    - Return [] for fewer than 2 samples.
    - Skip pairs where Δtime == 0 (can't divide) rather than crash.
    - This is for GAUGES: it does NOT correct for resets (a drop is a real decrease).
    """
    # TODO: pairwise-iterate; emit (Δvalue/Δtime) at the later timestamp.
    if len(samples) < 2:
        return []
    result = []
    for i in range(1, len(samples)):
        a, b = samples[i - 1], samples[i]
        dt = b.timestamp - a.timestamp
        if dt == 0:
            continue
        dv = b.value - a.value
        result.append(Sample(timestamp=b.timestamp, value=dv / dt))
    return result



def rate(samples: List[Sample], counter: bool = True) -> List[Sample]:
    """
    Per-second rate between consecutive samples, for a monotonically increasing
    counter. Like derivative but with COUNTER-RESET handling:

    - If counter is True and b.value < a.value, treat it as a reset: the counter
      restarted, so the increment over the interval is just b.value (the amount
      accumulated since the reset), NOT b.value - a.value (which is negative).
    - rate = increment / Δtime.  (Since we divide by Δtime in seconds, this is
      already "per second".)
    - Skip Δtime == 0 pairs. Return [] for < 2 samples.
    - counter=False falls back to plain derivative behavior (allow negatives).
    """
    # TODO: for each adjacent pair, compute delta = b.value - a.value; if counter and
    #       delta < 0 -> delta = b.value (reset correction); emit delta/Δtime.
    if len(samples) < 2:
        return []
    result = []
    for i in range(1, len(samples)):
        a, b = samples[i - 1], samples[i]
        dt = b.timestamp - a.timestamp
        if dt == 0:
            continue
        dv = b.value - a.value
        if counter and dv < 0:
            dv = b.value  # reset correction
        result.append(Sample(timestamp=b.timestamp, value=dv / dt))
    return result


def total_increase(samples: List[Sample], counter: bool = True) -> float:
    """
    Total increase of a counter across the whole series, correctly summing across
    resets. Equivalent to summing each interval's positive increment.

    Example: values [0, 5, 10, 2, 6] (reset between 10 and 2)
             increments: 5, 5, 2 (reset: use 2), 4  -> total 16
    Return 0.0 for < 2 samples.
    """
    # TODO: walk adjacent pairs; add (b.value - a.value) normally, or b.value on reset.
    if len(samples) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(samples)):
        a, b = samples[i - 1], samples[i]
        dv = b.value - a.value
        if counter and dv < 0:
            dv = b.value  # reset correction
        total += dv
    return total


def rate_over_window(samples: List[Sample], counter: bool = True) -> Optional[float]:
    """
    A single average rate across the entire window (Prometheus-style rate()):
        total_increase(samples) / (last.timestamp - first.timestamp)
    Return None for < 2 samples or zero time span.
    """
    # TODO: use total_increase and the overall time span.
    if len(samples) < 2:
        return None
    dt = samples[-1].timestamp - samples[0].timestamp
    if dt == 0:
        return None
    total = total_increase(samples, counter=counter)
    return total / dt


def samples_from_points(points: List[Dict[str, Any]], field_key: str = "value") -> List[Sample]:
    """Adapt the established point-dict stream into Samples, sorted by timestamp."""
    # TODO: build Sample(ts, point["fields"][field_key]) for numeric values, sorted.
    samples = []
    for point in points:
        ts = point["timestamp"]
        value = point["fields"][field_key]
        samples.append(Sample(timestamp=ts, value=value))
    samples.sort(key=lambda s: s.timestamp)
    return samples


def test_advanced_agg():
    print("Testing Advanced Aggregations...")

    # Test 1: derivative of a linear gauge is constant
    s = [Sample(0, 0), Sample(1, 10), Sample(2, 20), Sample(3, 30)]
    d = derivative(s)
    assert len(d) == 3
    assert all(abs(x.value - 10) < 1e-9 for x in d)
    assert d[0].timestamp == 1  # derivative stamped at the later point
    print("✓ Test 1 passed: derivative of linear series")

    # Test 2: derivative allows negatives (gauge going down)
    d = derivative([Sample(0, 100), Sample(10, 50)])
    assert abs(d[0].value - (-5.0)) < 1e-9   # (50-100)/10
    print("✓ Test 2 passed: derivative negative slope")

    # Test 3: rate of a clean counter (per second)
    # counter grows 0->30->90 over 0->10->30s: rates 3/s then 3/s
    s = [Sample(0, 0), Sample(10, 30), Sample(30, 90)]
    r = rate(s)
    assert abs(r[0].value - 3.0) < 1e-9 and abs(r[1].value - 3.0) < 1e-9
    print("✓ Test 3 passed: counter rate per second")

    # Test 4: counter reset handling (no phantom negative)
    # 100 -> 10 is a reset; increment since reset is 10 over the interval
    s = [Sample(0, 90), Sample(10, 100), Sample(20, 10)]
    r = rate(s, counter=True)
    assert r[0].value > 0 and r[1].value > 0, "no negative rates after reset"
    assert abs(r[1].value - 1.0) < 1e-9   # 10 / 10s
    print("✓ Test 4 passed: counter reset produces positive rate")

    # Test 5: counter=False lets the drop show as negative
    r = rate(s, counter=False)
    assert r[1].value < 0
    print("✓ Test 5 passed: non-counter rate allows negatives")

    # Test 6: total_increase across a reset
    s = [Sample(0, 0), Sample(1, 5), Sample(2, 10), Sample(3, 2), Sample(4, 6)]
    assert total_increase(s) == 16
    print("✓ Test 6 passed: total_increase across reset")

    # Test 7: rate_over_window average
    s = [Sample(0, 0), Sample(10, 100)]
    assert abs(rate_over_window(s) - 10.0) < 1e-9   # 100 increase / 10s
    assert rate_over_window([Sample(0, 5)]) is None  # single sample
    print("✓ Test 7 passed: rate_over_window")

    # Test 8: zero Δtime pairs skipped, adapter works
    pts = [
        {"timestamp": 2, "fields": {"value": 20}},
        {"timestamp": 0, "fields": {"value": 0}},
        {"timestamp": 2, "fields": {"value": 25}},  # duplicate ts=2
    ]
    sm = samples_from_points(pts)
    assert [x.timestamp for x in sm] == [0, 2, 2]  # sorted
    d = derivative(sm)
    # only the 0->2 pair is valid; the 2->2 pair (Δt=0) is skipped
    assert len(d) == 1 and abs(d[0].value - 10.0) < 1e-9
    print("✓ Test 8 passed: adapter + zero-Δtime skip")

    print("\n🎉 All advanced aggregation tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement derivative, rate, total_increase, rate_over_window,
       and samples_from_points.
    2. Run: python day21_advanced_agg.py
    3. All 8 tests should pass.

    Success criteria:
    - derivative gives Δvalue/Δtime and permits negatives (gauges)
    - rate normalizes to per-second and NEVER goes negative on a counter reset
    - total_increase sums correctly across one or more resets
    - Δtime == 0 pairs are skipped, not divided by

    Next steps:
    - Run the Week 3 Integration Lab: labs/week3_lab.py
    - Think about: why can't you distinguish a reset from a genuine counter that
      legitimately decreased? (You can't — that's why counters must be monotonic.)
    """
    test_advanced_agg()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Derivative vs Rate
   - Derivative = Δvalue/Δtime for gauges (temperature, queue depth) — negatives are
     meaningful. Rate = per-second change of a monotonic counter — negatives are
     nonsense and signal a reset.

2. Counter Resets
   - Counters restart at 0 on process restart/overflow. A raw difference then goes
     negative. The fix: when b < a, assume a reset and count the increment as b (what
     accumulated since restart). This can UNDERCOUNT (misses the pre-reset tail) but
     never produces a phantom negative — the safe, standard choice.

3. Rate Normalization
   - Dividing by Δtime in seconds makes rates comparable regardless of sample spacing
     (a 10s gap and a 60s gap yield the same units). Essential for irregular sampling.

4. Windowed Rate
   - rate() over a window = total increase / window span. Composing this with Day 18's
     windows gives "requests/sec per 5m", the canonical monitoring query.

Connection to InfluxDB / Prometheus:
- Prometheus `rate()`/`increase()` and Flux `derivative(nonNegative: true)` implement
  exactly this reset-aware differencing. `nonNegative: true` == your counter=True path.

Trade-offs:
- Reset correction can't recover the exact lost increment (data between last sample
  and the reset is gone), so counter rates are slightly under-counted right at a
  reset. This is accepted everywhere because the alternative — huge negative spikes —
  is far worse for alerting and dashboards.
"""
