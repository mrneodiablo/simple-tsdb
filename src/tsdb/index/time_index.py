#!/usr/bin/env python3

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
        if start > end:
            raise ValueError(f"start {start} must be <= end {end}")
        
        # TODO: cutoff = bisect.bisect_right(self._min_keys, end)
        cutoff = bisect.bisect_right(self._min_keys, end)

        # TODO: Filter self._blocks[:cutoff] by max_ts >= start
        result = [block for block in self._blocks[:cutoff] if block.max_ts >= start]
        return result
    
    def find_locations_in_range(self, start: float, end: float) -> List[str]:
        """Convenience: just the locations from find_blocks_in_range."""
        blocks = self.find_blocks_in_range(start, end)
        return [block.location for block in blocks]

    def time_bounds(self) -> Optional[Tuple[float, float]]:
        """
        Overall (min_ts, max_ts) across all blocks, or None if empty.
        Useful for answering "what's the full time span of my data?".
        """
        if not self._blocks:
            return None
        min_ts = self._blocks[0].min_ts
        max_ts = max(block.max_ts for block in self._blocks)
        return (min_ts, max_ts)

    def __len__(self) -> int:
        return len(self._blocks)

