#!/usr/bin/env python3
"""
Day 13: Range Query Optimization
================================

Problem: A big time-range query may touch many files, each already sorted by
time. Returning a global, time-ordered stream WITHOUT loading everything into
memory at once requires a k-way merge. Build a memory-efficient, streaming range
query.

Learning Objectives:
- Use iterators/generators to stream results lazily
- Implement a k-way merge of already-sorted streams with a heap
- Support LIMIT (stop early) and time-ordered output
- Reason about memory: O(k) buffered, not O(total points)

Real-World Connection:
TSM blocks are stored sorted by time. To answer a range query InfluxDB merges
many sorted block iterators into one ordered stream and stops as soon as LIMIT
is satisfied. You build the same merge engine here.
"""

import heapq
from typing import Dict, List, Any, Iterator, Iterable, Optional, Callable


def merge_sorted_streams(
    streams: List[Iterable[Dict[str, Any]]],
    key: Callable[[Dict[str, Any]], Any] = lambda p: p["timestamp"],
) -> Iterator[Dict[str, Any]]:
    """
    K-way merge of streams that are EACH already sorted by `key`.

    Yields items in globally sorted order using a heap of size <= k (number of
    streams), so memory stays O(k) regardless of total item count.

    Implementation hint:
    - Turn each iterable into an iterator.
    - Seed a heap with (key(first_item), stream_index, first_item) for each
      non-empty stream.
    - Pop the smallest; yield it; push the next item from THAT stream.
    - Use stream_index as a tie-breaker so dicts are never compared directly.
    """
    # TODO: build iterators, seed the heap with the first item of each
    # TODO: while heap: pop smallest, yield it, advance that stream
    raise NotImplementedError


class RangeQueryEngine:
    """
    Streams points within a time range across many sorted locations.

    Dependencies (injected, matching earlier days):
        time_index.find_locations_in_range(start, end) -> List[str]
        read_location(loc) -> Iterable[dict]   # points sorted by timestamp
    """

    def __init__(self, time_index, read_location: Callable[[str], Iterable[Dict[str, Any]]]):
        self.time_index = time_index
        self.read_location = read_location

    def _location_stream(self, location: str, start: float, end: float) -> Iterator[Dict[str, Any]]:
        """
        Yield in-range points from ONE location, lazily.

        Because the location is sorted by time you MAY break early once a point
        passes `end` (optional optimization). At minimum, filter to [start, end].
        """
        # TODO: iterate read_location(location); yield points with
        #       start <= ts <= end; optionally break when ts > end
        raise NotImplementedError

    def range_query(
        self, start: float, end: float, limit: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream all points in [start, end] in time order, across all locations.

        Steps:
        1. Ask the time index for candidate locations.
        2. Build a per-location filtered stream (self._location_stream).
        3. Merge them with merge_sorted_streams.
        4. If limit is set, yield at most `limit` points then stop (the merge
           is lazy, so unread locations are never fully loaded).
        """
        # TODO: locations = self.time_index.find_locations_in_range(start, end)
        # TODO: streams = [self._location_stream(loc, start, end) for loc ...]
        # TODO: yield from merge_sorted_streams(streams), respecting limit
        raise NotImplementedError

    def range_query_list(
        self, start: float, end: float, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Eager convenience wrapper returning a list (for tests / small ranges)."""
        # TODO: return list(self.range_query(...))
        raise NotImplementedError


def _pt(ts):
    return {"timestamp": ts, "tags": {}, "fields": {"v": ts}}


def test_range_queries():
    """Test cases for range query optimization."""
    print("Testing Range Query Optimization...")

    # Test 1: merge of sorted streams
    s1 = [_pt(1), _pt(4), _pt(7)]
    s2 = [_pt(2), _pt(3), _pt(8)]
    s3 = [_pt(5), _pt(6)]
    merged = list(merge_sorted_streams([s1, s2, s3]))
    assert [p["timestamp"] for p in merged] == [1, 2, 3, 4, 5, 6, 7, 8]
    print("✓ Test 1 passed: k-way merge produces globally sorted order")

    # Test 2: merge handles empty streams
    merged2 = list(merge_sorted_streams([[], s1, []]))
    assert [p["timestamp"] for p in merged2] == [1, 4, 7]
    print("✓ Test 2 passed: merge handles empty streams")

    # ---- Build a fake indexed store: 3 files, each time-sorted ----
    files = {
        "f1": [_pt(100), _pt(110), _pt(120)],
        "f2": [_pt(105), _pt(115), _pt(500)],
        "f3": [_pt(108), _pt(125)],
    }

    class FakeTimeIndex:
        bounds = {"f1": (100, 120), "f2": (105, 500), "f3": (108, 125)}
        def find_locations_in_range(self, start, end):
            return [loc for loc, (lo, hi) in self.bounds.items() if lo <= end and hi >= start]

    engine = RangeQueryEngine(FakeTimeIndex(), lambda loc: files[loc])

    # Test 3: range_query merges across files in time order
    res = engine.range_query_list(100, 130)
    ts = [p["timestamp"] for p in res]
    assert ts == sorted(ts), "results must be globally time-sorted"
    assert ts == [100, 105, 108, 110, 115, 120, 125], f"got {ts}"
    assert 500 not in ts, "out-of-range point must be filtered"
    print("✓ Test 3 passed: cross-file time-ordered range query")

    # Test 4: LIMIT stops early
    limited = engine.range_query_list(100, 600, limit=3)
    assert [p["timestamp"] for p in limited] == [100, 105, 108]
    print("✓ Test 4 passed: LIMIT returns first N in time order")

    # Test 5: streaming is lazy (generator, not a prebuilt list)
    gen = engine.range_query(100, 600)
    first = next(gen)
    assert first["timestamp"] == 100
    print("✓ Test 5 passed: range_query yields lazily")

    # Test 6: empty range
    assert engine.range_query_list(1000, 2000) == []
    print("✓ Test 6 passed: empty range yields nothing")

    print("\n🎉 All range query tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement merge_sorted_streams and the RangeQueryEngine methods.
    2. Run: python day13_range_queries.py
    3. All 6 tests should pass.

    Success criteria:
    - merge_sorted_streams uses a heap (O(k) memory) and never compares dicts
    - range_query is a generator; LIMIT stops work early
    - results across files are globally time-ordered

    Next steps:
    - Day 14 adds bloom filters + stats to skip files that definitely lack a tag.
    - Think about: how does early-break-on-`end` change worst-case I/O?
    """
    test_range_queries()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. K-Way Merge
   - Merging k sorted streams with a min-heap yields a globally sorted stream in
     O(N log k) time and O(k) memory. The heap always holds the current head of
     each stream.
   - Tie-break on a stable index so heterogeneous payloads (dicts) are never
     compared directly — comparing dicts raises TypeError in Python 3.

2. Lazy Iterators / Generators
   - Generators produce items on demand. Combined with the merge, a LIMIT query
     touches only as much data as it needs and frees the rest.

3. Streaming vs Materializing
   - Materializing loads everything (O(N) memory); streaming keeps O(k).
   - For range scans over large windows this is the difference between fitting
     in RAM and OOM.

Connection to InfluxDB:
- The TSM engine exposes block iterators sorted by time and merges them; query
  operators pull from the merged iterator and short-circuit on LIMIT.

Trade-offs:
- Early break on `end` reduces I/O when blocks extend past the range, but
  requires per-location sorted input (which we have).
- Heap merge adds log(k) overhead vs concatenate+sort, but bounds memory.
"""
