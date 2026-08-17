#!/usr/bin/env python3

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
        if query.tag_filters:
            tag_locs = self.tag_index.lookup_multiple(query.tag_filters)
        else:
            tag_locs = None  # no tag filtering

        # TODO: time_locs  = time_index.find_locations_in_range(...) if bounded
        if query.start_time != float("-inf") or query.end_time != float("inf"):
            time_locs = set(self.time_index.find_locations_in_range(query.start_time, query.end_time))
        else:
            time_locs = None  # no time filtering

        # TODO: combine via set intersection; build & return QueryPlan
        if tag_locs is not None and time_locs is not None:
            candidate_locations = list(tag_locs & time_locs)
            strategy = "intersected tag + time indexes"
            used_tag_index = True
            used_time_index = True
        elif tag_locs is not None:
            candidate_locations = list(tag_locs)
            strategy = "used tag index only"
            used_tag_index = True
            used_time_index = False
        elif time_locs is not None:
            candidate_locations = list(time_locs)
            strategy = "used time index only"
            used_tag_index = False
            used_time_index = True
        else:
            candidate_locations = []  # or all locations if you have a way to get them
            strategy = "no indexes used; full scan"
            used_tag_index = False
            used_time_index = False

        return QueryPlan(
            candidate_locations=candidate_locations,
            used_tag_index=used_tag_index,
            used_time_index=used_time_index,
            strategy=strategy,
        )

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
        plan = self.plan(query)

        # TODO: scan candidate_locations, filter by time + tags + field_predicate
        results = []
        for loc in plan.candidate_locations:
            points = self.read_location(loc)
            for p in points:
                if not (query.start_time <= p["timestamp"] <= query.end_time):
                    continue

                if not all(p["tags"].get(k) == v for k, v in query.tag_filters.items()):
                    continue

                if query.field_predicate is None or query.field_predicate(p["fields"]):
                    results.append(p)

        # TODO: sort results by timestamp and return
        results.sort(key=lambda p: p["timestamp"])
        return results

    def count(self, query: Query) -> int:
        """Return how many points match — without materializing them all."""
        # TODO: ideally stream and count; simplest correct version: len(execute)
        return len(self.execute(query))


def _point(ts, tags, fields):
    return {"timestamp": ts, "tags": tags, "fields": fields}

