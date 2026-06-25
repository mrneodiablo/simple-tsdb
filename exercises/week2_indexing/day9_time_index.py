#!/usr/bin/env python3
"""
Day 9: Time Range Indexing (Binary Search)
==========================================

Problem: Given a query time range [start, end], find ONLY the files/blocks that
could contain matching data — without scanning every file's contents.

Learning Objectives:
- Keep an index sorted by time and exploit that ordering
- Implement binary search (and understand Python's `bisect`)
- Reason about overlapping ranges (a query range vs a file's [min, max])
- Achieve O(log n) file selection instead of O(n)

Real-World Connection:
InfluxDB groups data into time-bounded "shards" and TSM blocks each carry a
min/max timestamp. Time-range queries first prune whole shards/blocks by their
bounds — exactly what your TimeRangeIndex does here.
"""

import bisect
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class TimeBlock:
    """
    A unit of storage tagged with its time bounds.

    `location` is a file path (Week 1 partitioning) or block id. min/max are the
    smallest and largest timestamps of the data inside it.
    """

    location: str
    min_ts: float
    max_ts: float

    def overlaps(self, start: float, end: float) -> bool:
        """
        True if this block's [min_ts, max_ts] intersects the query [start, end].

        Two ranges overlap iff: min_ts <= end AND max_ts >= start.
        """
        # TODO: Implement the standard interval-overlap test
        if self.min_ts <= end and self.max_ts >= start:
            return True
        else:
            return False


class TimeRangeIndex:
    """
    Index of TimeBlocks kept sorted by min_ts to enable binary search.

    Invariant: self._blocks is always sorted by (min_ts, max_ts).
    """

    def __init__(self) -> None:
        self._blocks: List[TimeBlock] = []
        # Parallel sorted list of min_ts values, so we can use the `bisect`
        # module directly (it can't key into objects on older Pythons).
        self._min_keys: List[float] = []

    # ----------------------------------------------------------------- writes
    def add_block(self, location: str, min_ts: float, max_ts: float) -> None:
        """
        Insert a block while preserving the sorted-by-min_ts invariant.

        Use bisect to find the insertion point in O(log n), then insert in O(n)
        (list insert). For bulk loads, prefer add_blocks() + a single sort.
        """
        # TODO: Validate min_ts <= max_ts
        if min_ts > max_ts:
            raise ValueError(f"min_ts {min_ts} must be <= max_ts {max_ts}")
        
        # TODO: Find insertion index with bisect.bisect_left on self._min_keys
        index = bisect.bisect_left(self._min_keys, min_ts)
        
        # TODO: Insert into BOTH self._blocks and self._min_keys at that index
        self._blocks.insert(index, TimeBlock(location, min_ts, max_ts))
        self._min_keys.insert(index, min_ts)

    def add_blocks(self, blocks: List[Tuple[str, float, float]]) -> None:
        """
        Bulk insert (location, min_ts, max_ts) tuples, then sort once.

        Faster than repeated add_block when building the index from scratch.
        """
        # TODO: Extend self._blocks with TimeBlock(...) for each tuple
        for location, min_ts, max_ts in blocks:
            if min_ts > max_ts:
                raise ValueError(f"min_ts {min_ts} must be <= max_ts {max_ts}")
            self._blocks.append(TimeBlock(location, min_ts, max_ts))

        # TODO: Sort self._blocks by (min_ts, max_ts)
        self._blocks.sort(key=lambda block: (block.min_ts, block.max_ts))
        
        # TODO: Rebuild self._min_keys from the sorted blocks
        self._min_keys = [block.min_ts for block in self._blocks]

    # ----------------------------------------------------------------- reads
    def find_blocks_in_range(self, start: float, end: float) -> List[TimeBlock]:
        """
        Return all blocks overlapping [start, end], in time order.

        Strategy (O(log n + k), k = number of results):
        1. A block can overlap only if its min_ts <= end. Use bisect_right on
           self._min_keys to find the cutoff index — everything past it starts
           too late and can be skipped.
        2. Among candidates [0, cutoff), keep those whose max_ts >= start.

        NOTE: step 2 still scans candidates because blocks are sorted by min_ts,
        not max_ts. That's fine for partitioned time-series data where blocks
        rarely overlap. (Think: what structure would remove this scan entirely?)
        """
        # TODO: Validate start <= end
        # TODO: cutoff = bisect.bisect_right(self._min_keys, end)
        # TODO: Filter self._blocks[:cutoff] by max_ts >= start
        raise NotImplementedError

    def find_locations_in_range(self, start: float, end: float) -> List[str]:
        """Convenience: just the locations from find_blocks_in_range."""
        # TODO
        raise NotImplementedError

    def time_bounds(self) -> Optional[Tuple[float, float]]:
        """
        Overall (min_ts, max_ts) across all blocks, or None if empty.
        Useful for answering "what's the full time span of my data?".
        """
        # TODO
        raise NotImplementedError

    def __len__(self) -> int:
        return len(self._blocks)


def test_time_index():
    """Test cases for the time range index."""
    print("Testing Time Range Index...")

    # Test 1: overlap helper
    b = TimeBlock("f", 100, 200)
    assert b.overlaps(150, 160) is True       # fully inside
    assert b.overlaps(50, 120) is True        # left overlap
    assert b.overlaps(180, 300) is True       # right overlap
    assert b.overlaps(201, 300) is False      # after
    assert b.overlaps(0, 99) is False         # before
    print("✓ Test 1 passed: TimeBlock.overlaps")

    # Test 2: add_block keeps sorted invariant
    idx = TimeRangeIndex()
    idx.add_block("c", 300, 400)
    idx.add_block("a", 100, 200)
    idx.add_block("b", 200, 300)
    assert [bl.location for bl in idx._blocks] == ["a", "b", "c"], "Must stay sorted by min_ts"
    print("✓ Test 2 passed: sorted insertion")

    # Test 3: range query in the middle
    found = idx.find_locations_in_range(250, 320)
    assert set(found) == {"b", "c"}, f"Expected b,c got {found}"
    print("✓ Test 3 passed: overlapping range query")

    # Test 4: query before everything
    assert idx.find_locations_in_range(0, 50) == []
    print("✓ Test 4 passed: empty result for non-overlapping range")

    # Test 5: bulk load + larger dataset
    idx2 = TimeRangeIndex()
    blocks = [(f"file_{i}", i * 100, i * 100 + 99) for i in range(100)]
    # shuffle-ish insertion order without random: reversed
    idx2.add_blocks(list(reversed(blocks)))
    assert len(idx2) == 100
    # query [550, 720] should hit files 5,6,7
    res = idx2.find_locations_in_range(550, 720)
    assert set(res) == {"file_5", "file_6", "file_7"}, f"got {res}"
    print("✓ Test 5 passed: bulk load + binary-search range query")

    # Test 6: time bounds
    lo, hi = idx2.time_bounds()
    assert lo == 0 and hi == 99 * 100 + 99
    print("✓ Test 6 passed: time_bounds")

    print("\n🎉 All time index tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement TimeBlock.overlaps and every TimeRangeIndex method.
    2. Run: python day9_time_index.py
    3. All 6 tests should pass.

    Success criteria:
    - find_blocks_in_range uses bisect (O(log n)) to find the cutoff
    - results are returned in time order
    - the sorted-by-min_ts invariant always holds after inserts

    Next steps:
    - Day 10 introduces series keys so tag + time indexes point at the same id.
    - Think about: if blocks overlap heavily, how would an interval tree help?
    """
    test_time_index()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Binary Search & bisect
   - On a sorted list, bisect finds an insertion point in O(log n).
   - bisect_right(keys, end) gives the count of blocks whose min_ts <= end —
     a clean upper bound on candidates.

2. Interval Overlap
   - [a, b] overlaps [c, d]  <=>  a <= d AND b >= c.
   - Getting this off-by-one wrong is the classic time-range bug.

3. Pruning vs Scanning
   - The index PRUNES files that cannot match, then the storage layer scans the
     survivors. Fewer files scanned = faster query.
   - Sorting by min_ts gives a cheap upper cutoff but still needs a max_ts
     filter pass. An interval tree / segment tree removes that pass at the cost
     of more complexity.

Connection to InfluxDB:
- Shards are time-bounded; the query planner drops shards entirely outside the
  range before touching TSM files.
- Each TSM block stores min/max time so the engine skips non-overlapping blocks.

Trade-offs:
- Sorted array: simple, cache-friendly, O(log n) search, O(n) insert.
- Interval tree: O(log n) insert AND query for overlaps, more code & pointers.
- For append-mostly, time-partitioned data, the sorted array is usually enough.
"""
