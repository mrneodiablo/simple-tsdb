#!/usr/bin/env python3

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

