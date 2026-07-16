#!/usr/bin/env python3
"""
Day 19: Group By Operations (group by tag values)
=================================================

Problem: "mean CPU" is less useful than "mean CPU PER region PER host". GROUP BY
partitions points into groups keyed by a chosen set of tag values, then aggregates
each group independently. The core technique is hash-based grouping: build a
dict from group-key -> aggregator in one streaming pass. This composes with Day 18
(group first, then window, or window then group).

Learning Objectives:
- Build a canonical, hashable group key from a subset of tags
- Partition a stream into groups with a single dict pass (hash grouping)
- Aggregate each group independently with an injected aggregator factory
- Handle points missing a grouping tag (a distinct "absent" group)
- Combine grouping with time windowing (group + window key)

Real-World Connection:
InfluxDB groups by the "series" (measurement + tag set) implicitly, and Flux's
`group(columns: ["region","host"])` re-partitions tables by those columns before a
reducer runs. SQL's `GROUP BY region, host` is the same hash-partition-then-reduce.
"""

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


def test_groupby():
    print("Testing Group By Operations...")

    points = [
        _pt("us", "a", 10), _pt("us", "a", 20),
        _pt("us", "b", 100),
        _pt("eu", "a", 5),
        _pt("eu", None, 7),   # missing host tag
    ]

    # Test 1: group key construction
    assert make_group_key(points[0], ["region"]) == ("us",)
    assert make_group_key(points[0], ["region", "host"]) == ("us", "a")
    assert make_group_key(points[4], ["region", "host"]) == ("eu", None)
    print("✓ Test 1 passed: make_group_key")

    engine = GroupByEngine(agg_factory=_sum_factory, field_key="value")

    # Test 2: group by single tag (sum of value)
    groups = engine.group(points, ["region"])
    by_key = {g.key: g for g in groups}
    assert by_key[("us",)].value == 130   # 10+20+100
    assert by_key[("eu",)].value == 12    # 5+7
    print("✓ Test 2 passed: group by region")

    # Test 3: counts per group
    assert by_key[("us",)].count == 3 and by_key[("eu",)].count == 2
    print("✓ Test 3 passed: per-group counts")

    # Test 4: group by two tags
    groups = engine.group(points, ["region", "host"])
    by_key = {g.key: g for g in groups}
    assert by_key[("us", "a")].value == 30
    assert by_key[("us", "b")].value == 100
    assert by_key[("eu", "a")].value == 5
    assert by_key[("eu", None)].value == 7   # missing-host group
    print("✓ Test 4 passed: group by region+host (incl. missing tag)")

    # Test 5: empty group_by -> one global group keyed by ()
    groups = engine.group(points, [])
    assert len(groups) == 1
    assert groups[0].key == () and groups[0].value == 142  # 10+20+100+5+7
    print("✓ Test 5 passed: global aggregate")

    # Test 6: results sorted by key deterministically
    groups = engine.group(points, ["region", "host"])
    keys = [g.key for g in groups]
    assert keys == sorted(keys, key=_sort_key)
    print("✓ Test 6 passed: deterministic sort order")

    # Test 7: group + window composite key
    tp = [
        _pt("us", "a", 10, ts=0), _pt("us", "a", 20, ts=30),   # window 0
        _pt("us", "a", 5, ts=90),                              # window 60
        _pt("eu", "a", 1, ts=10),                              # window 0
    ]
    win = lambda ts: (ts // 60) * 60  # 60s windows aligned to epoch
    gw = engine.group_windowed(tp, ["region"], win)
    assert gw[(("us",), 0)].value == 30
    assert gw[(("us",), 60)].value == 5
    assert gw[(("eu",), 0)].value == 1
    print("✓ Test 7 passed: grouped + windowed aggregation")

    # Test 8: empty input
    assert engine.group([], ["region"]) == []
    print("✓ Test 8 passed: empty input")

    print("\n🎉 All group-by tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement make_group_key, GroupByEngine.group, and group_windowed.
    2. Run: python day19_groupby.py
    3. All 8 tests should pass.

    Success criteria:
    - Group keys are hashable tuples with None for absent tags
    - One streaming pass builds all groups (dict of aggregators)
    - Empty group_by yields a single global aggregate
    - Grouping composes with time windows via a composite key

    Next steps:
    - Day 20: an optimizer that orders filter/group/aggregate stages for speed.
    - Think about: why is a tuple the right group key vs a concatenated string?
    """
    test_groupby()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Hash-Based Grouping
   - Partition-then-reduce: a single pass builds {group_key: aggregator}. O(n) time,
     O(#groups) memory. No sorting required, unlike sort-based grouping.

2. Canonical Group Keys
   - A tuple in the requested tag order is hashable, order-stable, and lets None mark
     an absent tag distinctly. Concatenating into a string risks delimiter collisions
     ("a|b|c") and loses type info — the same trap Day 10's series keys warned about.

3. Absent Tags Are a Group
   - A point missing a grouping tag isn't an error — it belongs to the (…, None, …)
     group. Dropping it silently would undercount; crashing would be fragile.

4. Composition
   - Grouping and windowing are both "assign each point a key, then reduce". Making
     the key a composite (group_key, window) unifies GROUP BY and aggregateWindow in
     one mechanism — this is how real engines implement "mean per host per 5m".

Connection to InfluxDB:
- Flux `group(columns: [...])` reshapes the stream into one table per key set; a
  following `mean()` reduces each. InfluxQL `GROUP BY host, time(5m)` is precisely the
  composite (tag, window) key you built in group_windowed.

Trade-offs:
- Hash grouping is fast but holds one aggregator per live group in memory; very high
  tag cardinality (millions of groups) can blow memory — the same cardinality problem
  Week 2's series manager tracked. Sort-based grouping trades speed for bounded memory.
"""
