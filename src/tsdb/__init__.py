"""
Simple Time-Series Database (TSDB)
===================================

A minimal implementation of a time-series database for learning purposes.

This package provides:
- Storage layer for persisting time-series data
- Indexing system for fast queries
- Query processing engine
- TCP server API

Usage:
    from tsdb import TimeSeriesDB

    db = TimeSeriesDB("data_directory")
    db.write("cpu_metrics", {"host": "server1"}, {"usage": 75.5})
    results = db.query("SELECT mean(usage) FROM cpu_metrics WHERE host='server1'")
"""

__version__ = "1.0.0"
__author__ = "Time-Series Database Learning Project"

# Core components will be imported as they are implemented
# from .storage import FileManager, DataPoint, TimeSeriesSerializer
# from .index import TagIndex, TimeIndex, SeriesManager
# from .query import QueryEngine, FilterProcessor, Aggregator
# from .server import TCPServer, QueryParser, Client

# Main database interface (will be implemented in Week 4)
# from .database import TimeSeriesDB

__all__ = [
    # Will be populated as components are implemented
    # "TimeSeriesDB",
    # "DataPoint",
    # "FileManager",
    # "TagIndex",
    # "QueryEngine",
    # "TCPServer"
]