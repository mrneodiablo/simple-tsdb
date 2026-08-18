#!/usr/bin/env python3

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


def _sum_factory():
    class _Sum:
        def __init__(self):
            self.s = 0.0
            self.seen = False
        def update(self, v):
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                self.s += v
                self.seen = True
        def result(self):
            return self.s if self.seen else None
    return _Sum()


# A group key is a tuple of (tag_value_or_None) in the SAME order as the requested
# group_by tags — a tuple so it's hashable and order-stable.
GroupKey = Tuple[Optional[str], ...]


def make_group_key(point: Dict[str, Any], group_by: List[str]) -> GroupKey:
    """
    Build the group key for a point given the ordered list of grouping tag names.
    A tag that's absent from the point contributes None (its own group), NOT a crash.

    Example: point tags {"region":"us","host":"a"}, group_by=["region","zone"]
             -> ("us", None)
    """
    # TODO: return tuple(point["tags"].get(tag) for tag in group_by)
    return tuple(point["tags"].get(tag) for tag in group_by)



@dataclass
class Group:
    """One group's identity and aggregated value."""
    key: GroupKey
    value: Optional[float]
    count: int


class GroupByEngine:
    """
    Hash-based grouping + per-group aggregation.

    Dependencies injected:
      - agg_factory: () -> aggregator with .update(value)/.result()
      - field_key:   which field to aggregate
    """

    def __init__(self, agg_factory: Callable[[], Any] = _sum_factory, field_key: str = "value"):
        self.agg_factory = agg_factory
        self.field_key = field_key

    def group(self, points: List[Dict[str, Any]], group_by: List[str]) -> List[Group]:
        """
        Partition points by their group key and aggregate each group.

        - One streaming pass: dict group_key -> aggregator (create lazily on first
          point of a group). Also track a per-group count.
        - group_by == [] means one single group keyed by the empty tuple () (global
          aggregate).
        - Return groups sorted by key (None sorts first — see _sort_key).
        """
        # TODO: fold points into {key: aggregator}; feed field value; track counts;
        #       build Group(...) list sorted by _sort_key(key).

        groups: Dict[GroupKey, Tuple[Any, int]] = {}
        for point in points:
            key = make_group_key(point, group_by)
            if key not in groups:
                groups[key] = (self.agg_factory(), 0)
            agg, count = groups[key]
            agg.update(point["fields"].get(self.field_key))
            groups[key] = (agg, count + 1)

        result = [Group(key=k, value=agg.result(), count=count) for k, (agg, count) in groups.items()]
        result.sort(key=lambda g: _sort_key(g.key))
        return result

    def group_windowed(
        self,
        points: List[Dict[str, Any]],
        group_by: List[str],
        window_start_fn: Callable[[float], float],
    ) -> Dict[Tuple[GroupKey, float], Group]:
        """
        Group by BOTH tags and time window. The composite key is
        (group_key, window_start). `window_start_fn(ts)` maps a timestamp to its
        window start (inject Day 18's window_start via a lambda).

        Return a dict {(group_key, window_start): Group}. Each Group.key is the
        group_key (tags only); the window start is in the dict key.
        """
        # TODO: fold into {(group_key, w): aggregator}; feed values; build Groups.
        groups: Dict[Tuple[GroupKey, float], Tuple[Any, int]] = {}
        for point in points:
            key = make_group_key(point, group_by)
            window_start = window_start_fn(point["timestamp"])
            composite_key = (key, window_start)
            if composite_key not in groups:
                groups[composite_key] = (self.agg_factory(), 0)
            agg, count = groups[composite_key]
            agg.update(point["fields"].get(self.field_key))
            groups[composite_key] = (agg, count + 1)

        return {
            (k, w): Group(key=k, value=agg.result(), count=count)
            for (k, w), (agg, count) in groups.items()
        }


def _sort_key(key: GroupKey):
    """Sort helper: make None comparable (sorts before any string)."""
    return tuple((v is not None, v) for v in key)


def _pt(region: str, host: Optional[str], value: float, ts: float = 0.0) -> Dict[str, Any]:
    tags = {"region": region}
    if host is not None:
        tags["host"] = host
    return {"measurement": "cpu", "timestamp": ts, "tags": tags, "fields": {"value": value}}

