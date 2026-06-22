"""
Indexing System for Time-Series Database
=======================================

This module provides indexing capabilities for fast data retrieval.

Components:
- TagIndex: Hash-based indexing for tag key-value pairs
- TimeIndex: Binary search indexing for time range queries
- SeriesManager: Manages unique series identifiers and cardinality
- IndexPersistence: Saves and loads indexes from disk

Design Principles:
- Hash-based tag indexing for O(1) lookups
- Binary search for time range queries
- In-memory indexes with disk persistence
- Cardinality tracking to prevent memory explosions
"""

# Components will be imported as they are implemented during Week 2
# from .tag_index import TagIndex
# from .time_index import TimeIndex
# from .series_manager import SeriesManager
# from .persistence import IndexPersistence

__all__ = [
    # "TagIndex",
    # "TimeIndex",
    # "SeriesManager",
    # "IndexPersistence"
]