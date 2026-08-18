#!/usr/bin/env python3

from __future__ import annotations
import math
from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Optional, Dict, Callable


def is_number(x: Any) -> bool:
    """True if x is a real, finite number we can aggregate (bool excluded)."""
    # TODO: return True only for int/float (NOT bool) that is finite (not NaN/inf)
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        return math.isfinite(x)
    return False


class Aggregator(ABC):
    """
    Streaming aggregator. Feed values with update(); read the answer with result().
    Non-numeric / None values should be ignored by update() (null handling).
    """

    @abstractmethod
    def update(self, value: Any) -> None:
        """Feed a single value into the aggregator."""
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
        if is_number(value):
            self._n += 1

    def result(self) -> Optional[float]:
        # TODO: return the count (as a number; 0 is valid, not None)
        return float(self._n)


class Sum(Aggregator):
    def __init__(self):
        self._sum = 0.0
        self._seen = False

    def update(self, value: Any) -> None:
        if is_number(value):
            self._sum += value
            self._seen = True

    def result(self) -> Optional[float]:
        # TODO: return the sum, or None if nothing valid was seen
        return self._sum if self._seen else None


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
        if is_number(value):
            self._n += 1
            delta = value - self._mean
            self._mean += delta / self._n

    def result(self) -> Optional[float]:
        # TODO: return running mean, or None if n == 0
        return self._mean if self._n > 0 else None


class Min(Aggregator):
    def __init__(self):
        self._min: Optional[float] = None

    def update(self, value: Any) -> None:
        # TODO: track the smallest numeric value seen
        if is_number(value):
            if self._min is None or value < self._min:
                self._min = value

    def result(self) -> Optional[float]:
        # TODO
        return self._min


class Max(Aggregator):
    def __init__(self):
        self._max: Optional[float] = None

    def update(self, value: Any) -> None:
        # TODO
        if is_number(value):
            if self._max is None or value > self._max:
                self._max = value

    def result(self) -> Optional[float]:
        # TODO
        return self._max


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
    if agg not in AGGREGATORS:
        raise KeyError(f"Unknown aggregator: {agg}")
    aggregator = AGGREGATORS[agg]()
    for point in points:
        value = point.get("fields", {}).get(field_key)
        aggregator.update(value)
    return aggregator.result()

