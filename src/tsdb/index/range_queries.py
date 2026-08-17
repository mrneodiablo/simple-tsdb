#!/usr/bin/env python3

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
    iterators = [iter(stream) for stream in streams]
    heap = []
    for i, it in enumerate(iterators):
        try:
            first_item = next(it)
            heap.append((key(first_item), i, first_item))
        except StopIteration:
            continue
    heapq.heapify(heap)

    # TODO: while heap: pop smallest, yield it, advance that stream
    while heap:
        _, i, item = heapq.heappop(heap)
        yield item
        try:
            next_item = next(iterators[i])
            heapq.heappush(heap, (key(next_item), i, next_item))
        except StopIteration:
            continue

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
        for point in self.read_location(location):
            ts = point["timestamp"]
            if ts < start:
                continue
            if ts > end:
                break
            yield point

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
        locations = self.time_index.find_locations_in_range(start, end)

        # TODO: streams = [self._location_stream(loc, start, end) for loc ...]
        streams = [self._location_stream(loc, start, end) for loc in locations]

        # TODO: yield from merge_sorted_streams(streams), respecting limit
        merged_stream = merge_sorted_streams(streams)
        count = 0
        for point in merged_stream:
            if limit is not None and count >= limit:
                break
            yield point
            count += 1
        

    def range_query_list(
        self, start: float, end: float, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Eager convenience wrapper returning a list (for tests / small ranges)."""
        # TODO: return list(self.range_query(...))
        return list(self.range_query(start, end, limit))

def _pt(ts):
    return {"timestamp": ts, "tags": {}, "fields": {"v": ts}}
