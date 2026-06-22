#!/usr/bin/env python3
"""
Day 8: Hash-Based Tag Indexing
==============================

Problem: Build an inverted index for tag-based lookups so queries don't have to
scan every data point on disk.

Learning Objectives:
- Understand the inverted index data structure (the heart of any search engine)
- Implement O(1) tag lookups using nested hash maps
- Combine multiple tag filters with AND / OR set operations
- Track tag cardinality (the #1 cause of TSDB memory problems)
- Connect the index back to the Week 1 storage layer (file locations / series ids)

Real-World Connection:
InfluxDB's TSI (Time Series Index) is, at its core, an inverted index that maps
each tag key/value to the set of series containing it. When you run
`WHERE host='server1' AND region='us-west'`, InfluxDB intersects two posting
lists instead of scanning data. You are about to build a miniature version.
"""

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


def test_tag_index():
    """Test cases for the hash-based tag index."""
    print("Testing Hash-Based Tag Index...")

    idx = TagIndex()

    # Test 1: basic add + lookup
    idx.add_entry("host", "server1", "loc1")
    idx.add_entry("host", "server1", "loc2")
    idx.add_entry("host", "server2", "loc3")
    idx.add_entry("region", "us-west", "loc1")
    idx.add_entry("region", "us-east", "loc2")
    idx.add_entry("region", "us-east", "loc3")

    assert idx.lookup("host", "server1") == {"loc1", "loc2"}
    assert idx.lookup("host", "missing") == set(), "Missing value must return empty set"
    print("✓ Test 1 passed: add_entry + lookup")

    # Test 2: idempotency
    idx.add_entry("host", "server1", "loc1")
    assert idx.lookup("host", "server1") == {"loc1", "loc2"}, "Duplicates must not grow the set"
    print("✓ Test 2 passed: idempotent inserts")

    # Test 3: indexing a whole data point
    point = {
        "measurement": "cpu",
        "timestamp": 1672531200.0,
        "tags": {"host": "server9", "region": "eu"},
        "fields": {"usage": 42.0},
    }
    idx.add_data_point(point, "loc9")
    assert "loc9" in idx.lookup("host", "server9")
    assert "loc9" in idx.lookup("region", "eu")
    print("✓ Test 3 passed: add_data_point indexes all tags")

    # Test 4: AND across tags  (host=server1 AND region=us-west -> loc1 only)
    res_and = idx.lookup_multiple({"host": "server1", "region": "us-west"}, MatchMode.AND)
    assert res_and == {"loc1"}, f"AND mismatch: {res_and}"
    print("✓ Test 4 passed: lookup_multiple AND (intersection)")

    # Test 5: OR across values (region=us-west OR region=us-east -> loc1,2,3)
    res_or = idx.lookup_multiple({"region": "us-west"}, MatchMode.OR)
    res_or |= idx.lookup("region", "us-east")
    assert res_or == {"loc1", "loc2", "loc3"}, f"OR mismatch: {res_or}"
    print("✓ Test 5 passed: union of posting lists")

    # Test 6: cardinality + inspection
    assert idx.cardinality("host") == 3, "host has server1, server2, server9"
    assert set(idx.get_tag_keys()) >= {"host", "region"}
    print("✓ Test 6 passed: cardinality + introspection")

    # Test 7: removal (retention / compaction)
    removed = idx.remove_location("loc1")
    assert removed >= 1
    assert "loc1" not in idx.lookup("host", "server1")
    print("✓ Test 7 passed: remove_location")

    # Test 8: stats
    stats = idx.stats()
    assert stats.tag_keys >= 2
    assert stats.total_postings >= 1
    print(f"✓ Test 8 passed: stats -> {stats}")

    print("\n🎉 All tag index tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement every method marked with `raise NotImplementedError`.
    2. Run: python day8_tag_index.py
    3. All 8 tests should pass.

    Success criteria:
    - lookup() is O(1) on the (key, value) pair, not O(n) over the data
    - lookup_multiple AND returns the intersection; OR returns the union
    - the index is idempotent and supports removal

    Next steps:
    - Day 9 adds a TIME index so you can also narrow by time range.
    - Think about: what happens to memory if a tag has 1,000,000 unique values?
    """
    test_tag_index()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Inverted Index
   - "Forward" mapping: location -> set of tags (how data is stored on disk).
   - "Inverted" mapping: tag -> set of locations (what makes search fast).
   - This is the exact structure behind Lucene/Elasticsearch and InfluxDB TSI.

2. Posting Lists
   - The set of locations under one (tag_key, tag_value) is a "posting list".
   - AND query = intersect posting lists; OR query = union them.
   - Optimization: intersect the SMALLEST posting list first to do less work.

3. Cardinality
   - Each distinct (measurement + tag set) is a "series".
   - High-cardinality tags (user_id, request_id, uuid) explode the number of
     series, and every series costs memory in the index.
   - Rule of thumb: tags are for things you filter/group by and have LOW
     cardinality; high-cardinality values belong in fields.

Connection to InfluxDB:
- TSI stores tag key -> value -> series id postings, persisted in files with an
  in-memory cache, plus bloom filters (you'll build one on Day 14).
- "Cardinality explosion" is the single most common InfluxDB production issue.

Trade-offs:
- Hash index: O(1) exact match, but cannot answer range queries on tag values
  (e.g. host > 'server5') — that needs a sorted/tree index.
- Memory vs speed: keeping postings in RAM is fast but bounded by cardinality.
"""
