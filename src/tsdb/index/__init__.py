"""
Indexing System for Time-Series Database
=======================================

Hash-based tag indexing, binary-search time indexing, series/cardinality management,
persistence, indexed reads, range queries, and bloom-filter optimization. Re-exports
each module's public API, e.g. `from tsdb.index import TagIndex, TimeRangeIndex`.
"""

from .tag_index import TagIndex, MatchMode, TagIndexStats
from .time_index import TimeRangeIndex, TimeBlock
from .series_keys import SeriesManager, CardinalityReport
from .index_persistence import IndexPersistence, IndexSerializer
from .read_ops import IndexedReader, Query, QueryPlan
from .range_queries import RangeQueryEngine, merge_sorted_streams
from .index_optimization import BloomFilter, BloomStats, OptimizedTagIndex

__all__ = [
    # tag_index
    "TagIndex", "MatchMode", "TagIndexStats",
    # time_index
    "TimeRangeIndex", "TimeBlock",
    # series_keys
    "SeriesManager", "CardinalityReport",
    # index_persistence
    "IndexPersistence", "IndexSerializer",
    # read_ops
    "IndexedReader", "Query", "QueryPlan",
    # range_queries
    "RangeQueryEngine", "merge_sorted_streams",
    # index_optimization
    "BloomFilter", "BloomStats", "OptimizedTagIndex",
]
