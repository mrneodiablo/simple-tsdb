#!/usr/bin/env python3
"""
Day 12: Read Operations Using Indexes
=====================================

Problem: Tie Day 8 (tag index) and Day 9 (time index) together into a single
query path. Given tag filters + a time range, use the indexes to pick the
SMALLEST set of locations, scan only those, and return matching data points.

Learning Objectives:
- Design a tiny Query object (what the caller asks for)
- Build a query plan: which index narrows the search the most?
- Intersect tag-matched locations with time-matched locations
- Apply predicate pushdown — filter while scanning, not after
- Return correct, time-ordered results

Real-World Connection:
This is a miniature query planner. InfluxDB does exactly this dance: use TSI to
find candidate series, prune shards/blocks by time, then read and filter.
Choosing the most selective index first is the core of cost-based planning.
"""

from typing import Dict, List, Any, Callable, Optional, Set
from dataclasses import dataclass, field


@dataclass
class Query:
    """A read request against the indexed store."""

    measurement: str
    tag_filters: Dict[str, str] = field(default_factory=dict)
    start_time: float = float("-inf")
    end_time: float = float("inf")
    # Optional field predicate applied during scan, e.g. lambda f: f["usage"] > 90
    field_predicate: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class QueryPlan:
    """The chosen execution strategy, useful for debugging/EXPLAIN."""

    candidate_locations: List[str] = field(default_factory=list)
    used_tag_index: bool = False
    used_time_index: bool = False
    strategy: str = ""  # human-readable description


class IndexedReader:
    """
    Executes Query objects using a TagIndex, a TimeRangeIndex, and a
    location-reader callback that loads raw points from a location.

    Dependencies are injected so this works with your Day 8/9 classes (or any
    object exposing the same small surface):
        tag_index.lookup_multiple(filters) -> Set[str]
        time_index.find_locations_in_range(start, end) -> List[str]
        read_location(location) -> List[dict]   # each dict has timestamp/tags/fields
    """

    def __init__(self, tag_index, time_index, read_location: Callable[[str], List[Dict[str, Any]]]):
        self.tag_index = tag_index
        self.time_index = time_index
        self.read_location = read_location

    # ----------------------------------------------------------------- plan
    def plan(self, query: Query) -> QueryPlan:
        """
        Decide which locations to scan.

        Steps:
        1. If there are tag filters, ask the tag index for matching locations.
        2. If the time range is bounded, ask the time index for its locations.
        3. Candidate set = intersection of whichever index(es) applied.
           (If neither applies, you must fall back to "all locations" — note
            that in the strategy string so the cost is visible.)
        4. Record what you used in the QueryPlan.

        Tip: intersect, don't union — both constraints must hold.
        """
        # TODO: tag_locs   = tag_index.lookup_multiple(...)  if tag_filters
        # TODO: time_locs  = time_index.find_locations_in_range(...) if bounded
        # TODO: combine via set intersection; build & return QueryPlan
        raise NotImplementedError

    # --------------------------------------------------------------- execute
    def execute(self, query: Query) -> List[Dict[str, Any]]:
        """
        Run the plan and return matching points, sorted by timestamp.

        For each candidate location:
            - read its points
            - keep points whose timestamp is within [start, end]
            - keep points whose tags match ALL tag_filters (the index narrows
              to files; you still verify per-point because a file can hold many
              series)
            - apply field_predicate if present (predicate pushdown)
        """
        # TODO: plan = self.plan(query)
        # TODO: scan candidate_locations, filter by time + tags + field_predicate
        # TODO: sort results by timestamp and return
        raise NotImplementedError

    def count(self, query: Query) -> int:
        """Return how many points match — without materializing them all."""
        # TODO: ideally stream and count; simplest correct version: len(execute)
        raise NotImplementedError


def _point(ts, tags, fields):
    return {"timestamp": ts, "tags": tags, "fields": fields}


def test_read_ops():
    """Test cases for indexed read operations."""
    print("Testing Indexed Read Operations...")

    # ---- Build a tiny in-memory world (no real disk needed) ----
    # Two files, each holding a few points.
    files = {
        "f1": [
            _point(100, {"host": "s1", "region": "us-west"}, {"usage": 10}),
            _point(150, {"host": "s1", "region": "us-west"}, {"usage": 95}),
        ],
        "f2": [
            _point(250, {"host": "s2", "region": "us-east"}, {"usage": 50}),
            _point(300, {"host": "s1", "region": "us-east"}, {"usage": 80}),
        ],
    }

    # Minimal fakes exposing the same surface as Day 8 / Day 9.
    class FakeTagIndex:
        def __init__(self):
            self.map = {
                ("host", "s1"): {"f1", "f2"},
                ("host", "s2"): {"f2"},
                ("region", "us-west"): {"f1"},
                ("region", "us-east"): {"f2"},
            }
        def lookup_multiple(self, filters, *_):
            sets = [self.map.get((k, v), set()) for k, v in filters.items()]
            if not sets:
                return set()
            out = set(sets[0])
            for s in sets[1:]:
                out &= s
            return out

    class FakeTimeIndex:
        bounds = {"f1": (100, 150), "f2": (250, 300)}
        def find_locations_in_range(self, start, end):
            return [loc for loc, (lo, hi) in self.bounds.items() if lo <= end and hi >= start]

    reader = IndexedReader(FakeTagIndex(), FakeTimeIndex(), lambda loc: files[loc])

    # Test 1: plan intersects tag + time indexes
    q = Query("cpu", {"host": "s1"}, start_time=0, end_time=200)
    plan = reader.plan(q)
    assert plan.used_tag_index and plan.used_time_index
    assert set(plan.candidate_locations) == {"f1"}, f"got {plan.candidate_locations}"
    print("✓ Test 1 passed: plan intersects tag + time candidates")

    # Test 2: execute returns only in-range, tag-matching points
    res = reader.execute(q)
    assert len(res) == 2 and all(p["tags"]["host"] == "s1" for p in res)
    assert [p["timestamp"] for p in res] == [100, 150], "must be time-sorted"
    print("✓ Test 2 passed: execute filters by tag + time, sorted")

    # Test 3: field predicate pushdown (usage > 90)
    q2 = Query("cpu", {"host": "s1"}, 0, 400, field_predicate=lambda f: f["usage"] > 90)
    res2 = reader.execute(q2)
    assert len(res2) == 1 and res2[0]["fields"]["usage"] == 95
    print("✓ Test 3 passed: field predicate pushdown")

    # Test 4: multi-tag AND narrows correctly
    q3 = Query("cpu", {"host": "s1", "region": "us-east"}, 0, 400)
    res3 = reader.execute(q3)
    assert len(res3) == 1 and res3[0]["timestamp"] == 300
    print("✓ Test 4 passed: multi-tag AND")

    # Test 5: count matches execute length
    assert reader.count(q) == len(reader.execute(q))
    print("✓ Test 5 passed: count consistent with execute")

    # Test 6: empty result for non-matching range
    q4 = Query("cpu", {"host": "s1"}, 1000, 2000)
    assert reader.execute(q4) == []
    print("✓ Test 6 passed: empty result outside range")

    print("\n🎉 All indexed read tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement IndexedReader.plan / execute / count.
    2. Run: python day12_read_ops.py
    3. All 6 tests should pass.

    Success criteria:
    - plan() intersects tag-index and time-index candidate locations
    - execute() verifies tags + time per point and applies field predicates
    - results come back sorted by timestamp

    Next steps:
    - Day 13 optimizes large time-range scans with streaming + k-way merge.
    - Think about: when is a full scan actually cheaper than using the index?
    """
    test_read_ops()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Query Planning
   - The plan decides WHICH data to touch; execution does the touching.
   - Use the most selective constraint first; intersect candidate sets so both
     tag and time constraints prune the search.

2. Predicate Pushdown
   - Filter as early/low as possible. Checking field_predicate during the scan
     avoids building a big list only to throw most of it away.

3. Index Narrows to Files, Scan Confirms Points
   - A file/location can hold many series and timestamps, so the index gives
     CANDIDATES; the scan still verifies each point. This two-level filtering is
     fundamental to all indexed databases.

Connection to InfluxDB:
- TSI -> candidate series; shard/block time bounds -> candidate blocks; the
  iterator then reads and applies remaining predicates. Same shape, more layers.

Trade-offs:
- Index lookup has overhead; for tiny datasets a full scan can win.
- Cost-based planners estimate result sizes to choose; here we use simple rules.
"""
