#!/usr/bin/env python3

from typing import Dict, List, Set, Any, Optional, Iterable
from dataclasses import dataclass, field
from enum import Enum


class MatchMode(Enum):
    """How to combine multiple tag filters."""

    AND = "and"  # location must match ALL filters (set intersection)
    OR = "or"    # location must match ANY filter (set union)


@dataclass
class TagIndexStats:
    """Summary statistics describing the current index."""

    tag_keys: int = 0
    tag_values: int = 0           # total (key, value) pairs
    total_postings: int = 0       # total entries across all posting lists
    indexed_locations: int = 0    # distinct locations referenced

    @property
    def average_postings_per_value(self) -> float:
        """Average posting-list length. Low value => high cardinality => $$$."""
        return self.total_postings / self.tag_values if self.tag_values else 0.0


class TagIndex:
    """
    Inverted index: tag_key -> tag_value -> set of locations.

    A "location" is whatever you use to find the underlying data again. In this
    learning project it can be a file path (from Week 1 partitioning) or a
    series id (Day 10). The index does not care what it points to.

    Structure:
        {
            "host":   {"server1": {"loc1", "loc2"}, "server2": {"loc3"}},
            "region": {"us-west": {"loc1"},         "us-east": {"loc2", "loc3"}},
        }
    """

    def __init__(self) -> None:
        # tag_key -> tag_value -> set of locations
        self._index: Dict[str, Dict[str, Set[str]]] = {}

    # ----------------------------------------------------------------- writes
    def add_entry(self, tag_key: str, tag_value: str, location: str) -> None:
        """
        Record that `location` contains the pair (tag_key=tag_value).

        Must be idempotent: adding the same triple twice changes nothing.
        """
        # TODO: Validate inputs are non-empty strings
        if not isinstance(tag_key, str) or not tag_key:
            raise ValueError("tag_key must be a non-empty string")
        if not isinstance(tag_value, str) or not tag_value:
            raise ValueError("tag_value must be a non-empty string")
        if not isinstance(location, str) or not location:
            raise ValueError("location must be a non-empty string")
        
        # TODO: Create the nested dict/set on first sight of key or value
        if tag_key not in self._index:
            self._index[tag_key] = {}
        if tag_value not in self._index[tag_key]:
            self._index[tag_key][tag_value] = set()

        # TODO: Add `location` to the posting set (sets dedupe for free)
        self._index[tag_key][tag_value].add(location)
        
    def add_data_point(self, data_point: Dict[str, Any], location: str) -> None:
        """
        Index every tag of a single data point.

        Args:
            data_point: dict with at least a "tags" mapping
                        (e.g. the .to_dict() output from Week 1's DataPoint)
                        {
                            "measurement": "cpu",
                            "timestamp": 1672531200.123,
                            "tags": {"host": "server1", "region": "us-west"},
                            "fields": {
                                "cpu_usage": {"value": 75.5, "type": "float"},
                                "active_processes": {"value": 42, "type": "integer"},
                                "hostname": {"value": "web-01", "type": "string"},
                                "is_healthy": {"value": true, "type": "boolean"}
                            }
                        }
            location:   where this point lives (file path or series id)
        """
        # TODO: Pull out data_point["tags"] (default to empty dict)
        tags = data_point.get("tags", {})
        
        # TODO: Call add_entry for each tag_key/tag_value
        for tag_key, tag_value in tags.items():
            self.add_entry(tag_key, tag_value, location)

    # ----------------------------------------------------------------- reads
    def lookup(self, tag_key: str, tag_value: str) -> Set[str]:
        """
        Return the set of locations matching a single tag = value.

        Returns an EMPTY set (not an error) when nothing matches — callers
        rely on this to keep set algebra clean.
        """
        # TODO: Safely navigate the nested dict and return a copy of the set
        return self._index.get(tag_key, {}).get(tag_value, set()).copy()

    def lookup_multiple(
        self, filters: Dict[str, str], mode: MatchMode = MatchMode.AND
    ) -> Set[str]:
        """
        Combine several tag filters.

        Args:
            filters: {tag_key: tag_value, ...}
            mode:    AND -> intersection of posting lists
                     OR  -> union of posting lists

        Examples:
            lookup_multiple({"host": "server1", "region": "us-west"})  # AND
            lookup_multiple({"host": "server1", "host": "server2"}, OR)
        """
        # TODO: Handle the empty-filters case (decide & document the behavior)
        if not filters:
            return set()  # Return empty set for no filters

        # TODO: AND  -> start from the first posting set, intersect the rest
        #       (tip: intersect the SMALLEST set first for speed)
        if mode == MatchMode.AND:
            posting_sets = [self.lookup(k,v) for k,v in filters.items()]
            if not posting_sets:
                return set()
            # Sort by size to intersect smallest first
            posting_sets.sort(key=len)
            result = posting_sets[0]
            for s in posting_sets[1:]:
                result &= s
            return result

        # TODO: OR   -> union all posting sets
        if mode == MatchMode.OR:
            posting_sets = [self.lookup(k,v) for k,v in filters.items()]
            result = set()
            for s in posting_sets:
                result |= s
            return result

    # ------------------------------------------------------------- inspection
    def get_tag_keys(self) -> List[str]:
        """Return all indexed tag keys (sorted for deterministic output)."""
        # TODO
        return sorted(self._index.keys())       

    def get_tag_values(self, tag_key: str) -> List[str]:
        """Return all known values for a tag key (sorted)."""
        # TODO
        return sorted(self._index.get(tag_key, {}).keys())

    def cardinality(self, tag_key: Optional[str] = None) -> int:
        """
        Number of distinct values.

        - tag_key given  -> distinct values for that key
        - tag_key is None -> total distinct (key, value) pairs (series-ish)
        """
        # TODO
        if tag_key is not None:
            return len(self._index.get(tag_key, {}))
        else:
            return sum(len(values) for values in self._index.values())

    def remove_location(self, location: str) -> int:
        """
        Remove `location` from every posting list (e.g. after a file is deleted
        by retention). Returns the number of posting lists it was removed from.

        Bonus: clean up tag values / keys that become empty.
        """
        # TODO
        removed_count = 0
        empty_keys = []
        for tag_key, values in self._index.items():
            empty_values = []
            for tag_value, locations in values.items():
                if location in locations:
                    locations.remove(location)
                    removed_count += 1
                    if not locations:
                        empty_values.append(tag_value)
            for tv in empty_values:
                del values[tv]
            if not values:
                empty_keys.append(tag_key)
        for tk in empty_keys:
            del self._index[tk]
        return removed_count

    def stats(self) -> TagIndexStats:
        """Compute index-wide statistics (see TagIndexStats)."""
        # TODO: Walk the nested structure once and tally the fields
        stats = TagIndexStats()
        stats.tag_keys = len(self._index)

        for values in self._index.values():
            stats.tag_values += len(values)
            for locations in values.values():
                stats.total_postings += len(locations)
                stats.indexed_locations += len(locations)
        return stats
