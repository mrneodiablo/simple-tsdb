"""
Storage Layer for Time-Series Database
=====================================

This module handles data persistence and retrieval.

Components:
- FileManager: Handles file operations and directory structure
- DataPoint: Represents a single time-series data point
- TimeSeriesSerializer: Handles serialization/deserialization
- Partitioner: Manages time-based data partitioning

Design Principles:
- Append-only writes for time-series data
- Time-based partitioning for efficient queries
- JSON format for human readability (learning focus)
- Atomic operations for data integrity
"""

# Components will be imported as they are implemented during Week 1
# from .file_operations import FileManager
# from .serialization import DataPoint, TimeSeriesSerializer
# from .partitioning import TimePartitioner

__all__ = [
    # "FileManager",
    # "DataPoint",
    # "TimeSeriesSerializer",
    # "TimePartitioner"
]