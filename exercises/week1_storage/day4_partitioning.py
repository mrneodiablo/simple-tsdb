#!/usr/bin/env python3
"""
Day 4: Time-Based Partitioning
==============================

Problem: Organize data files by time ranges for efficient queries and retention

Learning Objectives:
- Understand time-based partitioning strategies
- Implement configurable time intervals
- Design efficient file organization
- Handle partition boundaries and edge cases
- Timezone is important for any distributed system! ALWAYS use UTC for timestamps and partitioning.

Real-World Connection:
InfluxDB organizes data into shards (time-based partitions) to optimize:
- Query performance (scan only relevant time ranges)
- Retention policies (delete old partitions)
- Parallel processing (different time ranges in parallel)
- Storage efficiency (compress old data differently)
"""

from collections import Counter
import os
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from enum import Enum
import calendar


class PartitionInterval(Enum):
    """Supported partition interval types."""

    HOUR = "1h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1M"


class TimePartitioner:
    """
    Manages time-based partitioning of time-series data.

    Features:
    - Timezone-aware UTC handling for distributed systems
    - Configurable partition intervals (hour, day, week, month)
    - Efficient path generation for time ranges
    - Partition boundary calculations
    - Retention policy support
    - Query optimization helpers
    """

    def __init__(
        self, base_path: str, interval: PartitionInterval = PartitionInterval.DAY
    ):
        """
        Initialize time partitioner.

        Args:
            base_path: Root directory for data storage
            interval: Partition interval (hour, day, week, month)
        """
        # TODO: Initialize partitioner with configuration
        # Store base path, interval, create directory structure
        self.base_path = Path(base_path)
        self.interval = interval

    def get_partition_path(self, timestamp: float, measurement: str) -> Path:
        """
        Get the file path for a measurement at given timestamp.

        Args:
            timestamp: Unix timestamp
            measurement: Measurement name

        Returns:
            Path to the partition file

        Examples:
            timestamp=1672531200 (2023-01-01 00:00:00), measurement="cpu", interval=DAY
            -> Path("data/2023/01/01/cpu.json")

            timestamp=1672531200, measurement="cpu", interval=HOUR
            -> Path("data/2023/01/01/00/cpu.json")
        """
        # TODO: Convert timestamp to datetime
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        # TODO: Generate path based on partition interval
        parts = [self.base_path, dt.strftime("%Y")]
        if self.interval == PartitionInterval.MONTH:
            parts.append(dt.strftime("%m"))
        if self.interval == PartitionInterval.DAY:
            parts.append(dt.strftime("%m"))
            parts.append(dt.strftime("%d"))
        if self.interval == PartitionInterval.HOUR:
            parts.append(dt.strftime("%m"))
            parts.append(dt.strftime("%d"))
            parts.append(dt.strftime("%H"))

        # TODO: Include measurement in filename
        parts.append(f"{measurement}_metrics.json")

        return Path(*parts)

    def get_partition_boundaries(self, timestamp: float) -> Tuple[float, float]:
        """
        Get start and end timestamps for partition containing given timestamp.

        Args:
            timestamp: Unix timestamp

        Returns:
            Tuple of (partition_start, partition_end) timestamps

        Examples:
            timestamp=1672534800 (2023-01-01 01:00:00), interval=DAY
            -> (1672531200, 1672617599)  # Start and end of Jan 1st

            timestamp=1672534800, interval=HOUR
            -> (1672534800, 1672538399)  # Start and end of 1 AM hour

            Timeline of Hour 12:
            ├─ 12:00:00.000000  ← start_dt (what we want!)
            ├─ 12:15:30.500000
            ├─ 12:30:45.123456
            ├─ 12:45:30.123456  ← dt (input)
            └─ 12:59:59.999999  ← end of hour

            # No matter what time in hour 12 you give:
            dt = 12:15:00  → start_dt = 12:00:00
            dt = 12:30:00  → start_dt = 12:00:00
            dt = 12:45:30  → start_dt = 12:00:00  Always rounds down!
            dt = 12:59:59  → start_dt = 12:00:00
        """
        # TODO: Calculate partition boundaries based on interval
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        # TODO: Handle different intervals (hour, day, week, month)
        if self.interval == PartitionInterval.HOUR:

            start_dt = dt.replace(minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(hours=1) - timedelta(seconds=1)
            return (start_dt.timestamp(), end_dt.timestamp())

        if self.interval == PartitionInterval.DAY:
            start_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(days=1) - timedelta(seconds=1)
            return (start_dt.timestamp(), end_dt.timestamp())

        if self.interval == PartitionInterval.MONTH:
            start_dt = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_date = calendar.monthrange(dt.year, dt.month)[1]
            end_dt = start_dt.replace(
                day=last_date, hour=23, minute=59, second=59, microsecond=999999
            )

        # TODO: Return start and end timestamps
        return (start_dt.timestamp(), end_dt.timestamp())

    def list_partitions_in_range(
        self, start_time: float, end_time: float, measurement: str
    ) -> List[Path]:
        """
        List all partition files that might contain data in time range.

        Args:
            start_time: Query start timestamp
            end_time: Query end timestamp
            measurement: Measurement to query

        Returns:
            List of partition file paths to check

        Requirements:
        - Include all partitions that overlap with query range
        - Handle partition boundaries correctly
        - Return paths in chronological order
        - Skip non-existent partitions efficiently
        """
        partitions = []

        # TODO: Calculate which partitions overlap with query range
        start_dt = datetime.fromtimestamp(start_time, tz=timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        end_dt = datetime.fromtimestamp(end_time, tz=timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )

        while start_dt <= end_dt:
            # TODO: Generate partition paths for each relevant time period
            partition_path = self.get_partition_path(start_dt.timestamp(), measurement)

            # TODO: Filter to only existing files
            if partition_path.exists():
                partitions.append(partition_path)

            # Increment to next partition
            if self.interval == PartitionInterval.HOUR:
                start_dt += timedelta(hours=1)
            elif self.interval == PartitionInterval.DAY:
                start_dt += timedelta(days=1)
            elif self.interval == PartitionInterval.MONTH:
                # Move to first day of next month
                if start_dt.month != 12:
                    start_dt = start_dt.replace(
                        year=start_dt.year, month=start_dt.month + 1, day=1
                    )
                else:
                    start_dt = start_dt.replace(year=start_dt.year + 1, month=1, day=1)

        # TODO: Sort by time order
        # Synce we check partitions in order, they should already be sorted
        return partitions

    def get_partition_info(self, partition_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get information about a partition file.

        Args:
            partition_path: Path to partition file

        Returns:
            Dictionary with partition metadata:
            - start_time: Partition start timestamp
            - end_time: Partition end timestamp
            - point_count: Number of data points
            - file_size: File size in bytes
            - measurement: Measurement name
            - last_modified: File modification time

        Returns None if file doesn't exist or is invalid.
        """
        # TODO: Check if file exists
        if not partition_path.exists():
            return None

        # TODO: Read file metadata (size, modification time)
        file_stats = partition_path.stat()
        file_size = file_stats.st_size
        last_modified = file_stats.st_mtime
        measurement = partition_path.stem.replace("_metrics", "")

        # TODO: Calculate partition time boundaries
        # Extract timestamp from path
        parts = partition_path.parts

        # since we don't know partition interval here, we infer it from path length
        # Assuming base_path is at index 0
        # Path structure examples:
        # data/2023/01/01/cpu_metrics.json  -> DAY
        # data/2023/01/01/00/cpu_metrics.json -> HOUR
        # data/2023/01/cpu_metrics.json -> MONTH
        # We can determine interval by counting parts after base_path
        if self.interval == PartitionInterval.HOUR:
            year = int(parts[-5])
            month = int(parts[-4])
            day = int(parts[-3])
            hour = int(parts[-2])
            start_dt = datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)
            end_dt = start_dt + timedelta(hours=1) - timedelta(seconds=1)
        elif self.interval == PartitionInterval.DAY:
            year = int(parts[-4])
            month = int(parts[-3])
            day = int(parts[-2])
            hour = 0
            start_dt = datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)
            end_dt = start_dt + timedelta(days=1) - timedelta(seconds=1)
        elif self.interval == PartitionInterval.MONTH:
            year = int(parts[-3])
            month = int(parts[-2])
            day = 1
            hour = 0
            start_dt = datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)
            last_date = calendar.monthrange(year, month)[1]
            end_dt = start_dt.replace(
                day=last_date, hour=23, minute=59, second=59, microsecond=999999
            )
        else:
            return None

        partition_start = start_dt.timestamp()
        partition_end = end_dt.timestamp()

        # TODO: Optionally count data points (expensive but useful)
        point_count = 0
        try:
            with open(partition_path, "r") as f:
                data = json.load(f)
                point_count = len(data)
        except Exception:
            return None

        return {
            "start_time": partition_start,
            "end_time": partition_end,
            "point_count": point_count,
            "file_size": file_size,
            "measurement": measurement,
            "last_modified": last_modified,
        }

    def cleanup_old_partitions(self, retention_days: int) -> Dict[str, Any]:
        """
        Remove partition files older than retention period.

        Args:
            retention_days: Number of days to keep data

        Returns:
            Dictionary with cleanup statistics:
            - files_removed: Number of files deleted
            - bytes_freed: Bytes of storage freed
            - oldest_kept: Timestamp of oldest remaining data
            - partitions_scanned: Total partitions checked

        Requirements:
        - Only delete complete partitions (not partial)
        - Handle different partition intervals correctly
        - Be safe - don't delete recent data by mistake
        - Return detailed statistics
        """
        # TODO: Calculate cutoff timestamp
        cutoff_time = time.time() - (retention_days * 86400)  # seconds in a day

        # TODO: Find partitions older than cutoff
        stats = {
            "files_removed": 0,
            "bytes_freed": 0,
            "oldest_kept": None,
            "partitions_scanned": 0,
        }

        # since we only delete complete partitions,
        # so if we have partition interval is DAY, we only delete partitions older than cutoff_time - 1 day
        if self.interval == PartitionInterval.HOUR:
            # we should round down cutoff_time to the previous hour
            cutoff_time = cutoff_time - 3600  # 1 hour
        elif self.interval == PartitionInterval.DAY:
            cutoff_time = cutoff_time - 86400  # 1 day
        elif self.interval == PartitionInterval.MONTH:
            # to be safe we consider month as 31 days
            cutoff_time = cutoff_time - (30 * 86400)  # Approx 1 month

        # TODO: Walk through all folder only under base_path
        # so folder structure is like:
        # base_path/year/month/day/hour/
        # base_path/year/month/day/
        # base_path/year/month/
        # how we get list distict partition folder under base_path?

        for file_path in self.base_path.rglob("*_metrics.json"):
            if self.interval == PartitionInterval.HOUR:
                year = int(file_path.parts[-5])
                month = int(file_path.parts[-4])
                day = int(file_path.parts[-3])
                hour = int(file_path.parts[-2])
                partition_dt = datetime(
                    year, month, day, hour, 0, 0, tzinfo=timezone.utc
                )
            elif self.interval == PartitionInterval.DAY:
                year = int(file_path.parts[-4])
                month = int(file_path.parts[-3])
                day = int(file_path.parts[-2])
                partition_dt = datetime(year, month, day, 0, 0, 0, tzinfo=timezone.utc)
            elif self.interval == PartitionInterval.MONTH:
                year = int(file_path.parts[-3])
                month = int(file_path.parts[-2])
                partition_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
            else:
                continue
            partition_time = partition_dt.timestamp()

            # TODO: Collect and return cleanup statistics
            stats["partitions_scanned"] += 1
            if partition_time < cutoff_time:
                try:
                    file_size = file_path.stat().st_size
                    # TODO: Safely delete old partition files
                    # using unlink to delete folder
                    file_path.unlink()
                    stats["files_removed"] += 1
                    stats["bytes_freed"] += file_size
                except Exception:
                    continue
            else:
                if (
                    stats["oldest_kept"] is None
                    or partition_time < stats["oldest_kept"]
                ):
                    stats["oldest_kept"] = partition_time

        return stats

    def estimate_partition_count(self, days: int) -> int:
        """
        Estimate number of partitions for given time period.

        Args:
            days: Number of days of data

        Returns:
            Estimated partition count

        Useful for:
        - Storage planning
        - Query performance estimation
        - Retention policy configuration
        """
        # TODO: Calculate partitions per day based on interval
        # TODO: Multiply by number of days
        # TODO: Consider measurement multipliers if needed

        if self.interval == PartitionInterval.HOUR:
            return days * 24
        elif self.interval == PartitionInterval.DAY:
            return days
        elif self.interval == PartitionInterval.MONTH:
            return (days + 29) // 30  # Approximate months
        else:
            return 0

    def optimize_partition_interval(
        self, write_rate: float, query_patterns: Dict[str, Any]
    ) -> PartitionInterval:
        """
        Recommend optimal partition interval based on usage patterns.

        Args:
            write_rate: Average data points per second
            query_patterns: Dictionary describing typical queries:
                - avg_query_range_hours: Average query time range
                - queries_per_second: Query rate
                - retention_days: Data retention period

        Returns:
            Recommended partition interval

        Optimization Factors:
        - Higher write rates prefer larger partitions (less file overhead)
        - Shorter queries prefer smaller partitions (less data to scan)
        - Longer retention prefers larger partitions (fewer files to manage)
        """
        # TODO: Analyze write patterns
        # Validate inputs
        if write_rate <= 0:
            return PartitionInterval.DAY  # Safe default

        recommendations = []

        # 1. Write throughput analysis
        points_per_h = write_rate * 3600
        bytes_per_h = points_per_h * 100  # Avg 100 bytes/point

        # Target: Keep partition files around 256MB (InfluxDB best practice)
        # Why 256MB? Balance between:
        # - Compression efficiency (larger = better compression)
        # - Query scan time (smaller = less to scan)
        # - File management overhead (fewer files = easier to manage)

        # so bytes_per_h throughput avg should be: 256MB / 30 days / 24 hours = 0.35MB per hour
        if bytes_per_h <= (256 * 1024 * 1024 / 30 / 24):  # ~0.35MB
            # Very low write rate → can use MONTH partitions
            recommendations.append(PartitionInterval.MONTH)

        # bytes_per_h * 24 = 1 Day <= 256MB => use DAY partition
        elif (bytes_per_h * 24) <= 256 * 1024 * 1024:
            # Moderate write rate → DAY partitions optimal
            recommendations.append(PartitionInterval.DAY)

        # bytes_per_h * 24 * 30 = 1 Month <= 256MB => use HOUR partition
        else:
            # High write rate → need HOUR partitions to keep files small
            recommendations.append(PartitionInterval.HOUR)

        # for recommendation is difficult i want to use strategy is get the most happend PartitionInterval in recommendations
        # return the most recommended partition interval, so each attribute we evaluate separately

        # TODO: Consider query patterns
        # 2. Query pattern analysis
        avg_query_hours = query_patterns.get("avg_query_range_hours", 24)

        if avg_query_hours <= 1:
            # Short queries → smaller partitions reduce scan time
            recommendations.append(PartitionInterval.HOUR)
        elif avg_query_hours <= 24:
            # Medium queries → day partitions are efficient
            recommendations.append(PartitionInterval.DAY)
        else:
            # Long-range queries → larger partitions reduce file count
            recommendations.append(PartitionInterval.MONTH)

        # 3. Query frequency analysis
        qps = query_patterns.get("queries_per_second", 0)

        if qps >= 10:
            # High query load → smaller partitions for better cache locality
            recommendations.append(PartitionInterval.HOUR)
        elif qps >= 1:
            # Medium query load → day partitions balance well
            recommendations.append(PartitionInterval.DAY)
        else:
            # Low query load → can use larger partitions
            recommendations.append(PartitionInterval.MONTH)

        # 4. Retention policy analysis
        retention_days = query_patterns.get("retention_days", 30)

        if retention_days <= 7:
            # Short retention → hourly for fine-grained cleanup
            recommendations.append(PartitionInterval.HOUR)
        elif retention_days <= 90:
            # Medium retention → daily is practical
            recommendations.append(PartitionInterval.DAY)
        else:
            # Long retention → monthly reduces file count
            recommendations.append(PartitionInterval.MONTH)

        # TODO: Balance file count vs scan efficiency
        counter = Counter(recommendations)
        most_common = counter.most_common(1)

        # TODO: Return optimal interval recommendation
        if most_common:
            return most_common[0][0]

        # Fallback: Safe default
        return PartitionInterval.DAY


class PartitionMetadata:
    """
    Tracks metadata for partition files to optimize queries.
    This includes tracking min/max timestamps, data point counts, file sizes, and tag value sets.
    This metadata can be used to skip irrelevant partitions during queries.

    Features:
    - Min/max timestamps per partition
    - Data point counts
    - File sizes and locations
    - Index into partition contents
    """

    def __init__(self, metadata_path: Optional[Path] = None):
        """Initialize empty metadata store."""
        # TODO: Initialize metadata storage
        # Consider: How to store and persist this metadata?
        self.metadata_store = {}  # Dict[str, Any]
        self.metadata_path = Path(metadata_path) if metadata_path else None

        if self.metadata_path and self.metadata_path.exists():
            self._load_metadata()

    def _load_metadata(self) -> None:
        """Load metadata from disk
        Load metadata from disk.
        wait we have config interval so metadata will be vary
        based on partition interval. but for now we just load simple json file
        meta data structure:
        # Metadata index (stored separately, ~1KB per partition):
        metadata = {
            "data/2023/01/15/cpu_metrics.json": {
                "min_timestamp": 1673740800,
                "max_timestamp": 1673827199,
                "point_count": 86400,
                "tags": {
                    "host": ["server1", "server2", "server3"],  # ← List of ALL hosts!
                    "region": ["us-west"]
                }
            }
        }
        """
        if not self.metadata_path or not self.metadata_path.exists():
            return

        with open(self.metadata_path, "r") as f:
            self.metadata_store = json.load(f)

    def _save_metadata(self) -> None:
        """Persist metadata to disk."""
        if not self.metadata_path:
            return

        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata_store, f, indent=2)

    def update_partition_metadata(
        self, partition_path: Path, data_points: List[Dict[str, Any]]
    ) -> None:
        """
        Update metadata for a partition after writing data.

        data_point: {"timestamp": 1764509839.701779, "tags": {"host": "server1", "region": "us-west"}, "fields": {"cpu_usage": 75.5, "memory_usage": 60.2}}

        Args:
            partition_path: Path to partition file
            data_points: Data points written to partition

        Updates:
        - Min/max timestamps
        - Point count increment
        - Tag value sets (for query optimization)
        - File size
        """
        if not data_points:
            return

        partition_str = str(partition_path)
        if partition_str not in self.metadata_store:
            self.metadata_store[partition_str] = {
                "min_timestamp": float("inf"),
                "max_timestamp": float("-inf"),
                "point_count": 0,
                "tags": {},
            }

        # load existing metadata for update as atomic operation
        partition_meta = self.metadata_store[partition_str]

        # TODO: Calculate min/max timestamps from data points
        timestamps = [dp["timestamp"] for dp in data_points]
        min_ts = min(timestamps)
        if min_ts < partition_meta["min_timestamp"]:
            partition_meta["min_timestamp"] = min_ts
        max_ts = max(timestamps)
        if max_ts > partition_meta["max_timestamp"]:
            partition_meta["max_timestamp"] = max_ts

        # TODO: Count data points
        point_count = len(data_points)
        partition_meta["point_count"] += point_count

        # TODO: Extract unique tag values
        tags = partition_meta["tags"]
        for dp in data_points:
            for tag_key, tag_values in dp.get("tags", {}).items():
                if tag_key not in tags:
                    tags[tag_key] = set()
                tags[tag_key].add(tag_values)

        # Convert sets to lists for JSON serialization
        for tag_key in partition_meta["tags"]:
            partition_meta["tags"][tag_key] = list(partition_meta["tags"][tag_key])

        # TODO: Store metadata efficiently
        # reasign back to metadata store & save to disk
        self.metadata_store[partition_str] = partition_meta
        self._save_metadata()

    def get_partitions_for_query(
        self, start_time: float, end_time: float, tag_filters: Dict[str, str]
    ) -> List[Path]:
        """
        Use metadata to find relevant partitions for query.

        Args:
            start_time: Query start time
            end_time: Query end time
            tag_filters: Tag filters from query {"host": "server1", "region": "us-west"}

        Returns:
            List of partition paths that might contain matching data

        Optimizations:
        - Skip partitions outside time range
        - Skip partitions without matching tag values
        - Return partitions in optimal scan order
        """
        relevant_partitions = []

        # TODO: Filter partitions by time range using metadata
        for partition_path, meta in self.metadata_store.items():
            if meta["max_timestamp"] < start_time:
                continue  # Skip partitions outside time range
            if meta["min_timestamp"] > end_time:
                continue  # Skip partitions outside time range

            # TODO: Filter by tag values if available in metadata
            skip_partition = False
            for tag_key, tag_value in tag_filters.items():
                if tag_key in meta["tags"]:
                    if tag_value not in meta["tags"][tag_key]:
                        skip_partition = True
                        # if one tag value not present we can skip this partition, since AND condition
                        break  # Tag value not present in this partition
                else:
                    skip_partition = True
                    # if one tag value not present we can skip this partition, since AND condition
                    break  # Tag key not present in this partition

            if skip_partition:
                continue  # Skip this partition

            relevant_partitions.append(Path(partition_path))
        # TODO: Sort by scan efficiency
        # use min_timestamp to sort for optimal scan order
        relevant_partitions.sort(
            key=lambda p: self.metadata_store[str(p)]["min_timestamp"]
        )

        return relevant_partitions


def test_time_partitioner():
    """
    Test cases for time partitioner.
    """
    print("Testing Time Partitioner...")

    # Setup test environment
    import tempfile
    import shutil

    test_dir = tempfile.mkdtemp()

    try:
        # Test 1: Basic partition path generation
        partitioner = TimePartitioner(test_dir, PartitionInterval.DAY)

        # Test with known timestamp: 2023-01-01 12:00:00 UTC
        test_timestamp = 1672574400
        path = partitioner.get_partition_path(test_timestamp, "cpu")

        expected_parts = ["2023", "01", "01", "cpu_metrics.json"]
        for part in expected_parts:
            assert part in str(path), f"Expected '{part}' in path '{path}'"
        print("✓ Test 1 passed: Basic partition path generation")

        # Test 2: Different partition intervals
        hourly = TimePartitioner(test_dir, PartitionInterval.HOUR)
        daily = TimePartitioner(test_dir, PartitionInterval.DAY)
        monthly = TimePartitioner(test_dir, PartitionInterval.MONTH)

        timestamp = 1672574400  # 2023-01-01 12:00:00

        hour_path = hourly.get_partition_path(timestamp, "cpu")
        day_path = daily.get_partition_path(timestamp, "cpu")
        month_path = monthly.get_partition_path(timestamp, "cpu")

        # Hour path should include hour directory
        assert "12" in str(hour_path), f"Hour not in hourly path: {hour_path}"
        # Day path should not include hour
        assert "12" not in str(day_path), f"Hour found in daily path: {day_path}"
        print("✓ Test 2 passed: Different partition intervals")

        # Test 3: Partition boundaries
        boundaries = partitioner.get_partition_boundaries(test_timestamp)
        start_time, end_time = boundaries

        # Should be start and end of the day
        start_dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(end_time, tz=timezone.utc)

        assert (
            start_dt.hour == 0 and start_dt.minute == 0
        ), f"Day should start at midnight: {start_dt}"
        assert (
            end_dt.hour == 23 and end_dt.minute == 59
        ), f"Day should end at 23:59: {end_dt}"
        print("✓ Test 3 passed: Partition boundaries")

        # Test 4: Create some test partition files
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Write test data to partition
        test_data = [
            {"timestamp": test_timestamp, "value": 1},
            {"timestamp": test_timestamp + 3600, "value": 2},
        ]

        with open(path, "w") as f:
            json.dump(test_data, f)

        # Test partition info
        info = partitioner.get_partition_info(path)
        assert info is not None, "Should get partition info for existing file"
        assert info["file_size"] > 0, "File size should be > 0"
        assert "measurement" in info, "Should include measurement info"
        print("✓ Test 4 passed: Partition info extraction")

        # Test 5: Range queries
        query_start = test_timestamp - 3600  # 1 hour before
        query_end = test_timestamp + 3600  # 1 hour after

        partitions = partitioner.list_partitions_in_range(query_start, query_end, "cpu")

        # Should find the partition we created
        assert len(partitions) > 0, "Should find partitions in range"
        assert path in partitions, f"Should find created partition {path}"
        print("✓ Test 5 passed: Range query partition listing")

        # Test 6: Partition interval optimization
        # Simulate high write rate, short queries
        write_rate = 1000.0  # 1000 points/second
        query_patterns = {
            "avg_query_range_hours": 1,  # 1-hour queries
            "queries_per_second": 10,
            "retention_days": 30,
        }

        recommended = partitioner.optimize_partition_interval(
            write_rate, query_patterns
        )
        assert isinstance(
            recommended, PartitionInterval
        ), "Should return PartitionInterval"
        print("✓ Test 6 passed: Partition interval optimization")

        # Test 7: Cleanup old partitions
        current_time = time.time()

        # Create RECENT partition (5 days ago - should KEEP)
        recent_timestamp = current_time - (5 * 24 * 3600)
        recent_path = partitioner.get_partition_path(recent_timestamp, "cpu")
        os.makedirs(os.path.dirname(recent_path), exist_ok=True)

        with open(recent_path, "w") as f:
            json.dump([{"timestamp": recent_timestamp, "value": 50}], f)

        # Create old partition
        old_timestamp = current_time - (40 * 24 * 3600)  # 40 days ago
        old_path = partitioner.get_partition_path(old_timestamp, "cpu")
        os.makedirs(os.path.dirname(old_path), exist_ok=True)

        with open(old_path, "w") as f:
            json.dump([{"timestamp": old_timestamp, "value": 99}], f)

        # Verify both files exist before cleanup
        assert os.path.exists(
            recent_path
        ), "Recent partition should exist before cleanup"
        assert os.path.exists(old_path), "Old partition should exist before cleanup"

        # Cleanup with 30-day retention
        cleanup_stats = partitioner.cleanup_old_partitions(retention_days=30)

        # Verify cleanup results
        assert cleanup_stats["files_removed"] > 0, "Should remove old files"
        assert not os.path.exists(
            old_path
        ), f"Old partition should be deleted: {old_path}"
        assert os.path.exists(
            recent_path
        ), f"Recent partition should remain: {recent_path}"
        print("✓ Test 7 passed: Old partition cleanup")

        # Test 8: Metadata tracking
        metadata = PartitionMetadata()

        metadata.update_partition_metadata(path, test_data)

        # Test query optimization
        tag_filters = {"host": "server1"}
        relevant_partitions = metadata.get_partitions_for_query(
            query_start, query_end, tag_filters
        )

        # Should return partition list (may be empty if no tag metadata)
        assert isinstance(relevant_partitions, list), "Should return list of partitions"
        print("✓ Test 8 passed: Partition metadata tracking")

        print("\n🎉 All time partitioner tests passed!")
        print("Your partitioner correctly handles:")
        print("  - Time-based partition path generation")
        print("  - Multiple partition intervals (hour, day, month)")
        print("  - Partition boundary calculations")
        print("  - Range query optimization")
        print("  - Retention policy enforcement")
        print("  - Metadata tracking for query optimization")

    finally:
        # Cleanup test directory
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    """
    Instructions:
    1. Implement all TODO methods in TimePartitioner and PartitionMetadata classes
    2. Run this file to test: python day4_partitioning.py
    3. All tests should pass
    4. Experiment with different partition intervals

    Success criteria:
    - All 8 tests pass
    - Partition paths generated correctly for all intervals
    - Boundary calculations are accurate
    - Range queries return correct partitions
    - Cleanup respects retention policies
    - Metadata tracking works

    Next steps:
    - Move to day5_write_ops.py
    - Think about: How would partitioning work in a distributed system?
    - Consider: What other partitioning strategies could work? (by measurement, by tag values)
    """
    test_time_partitioner()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts Learned:

1. Partitioning Strategies:
   - Time-based partitioning for time-series data
   - Horizontal vs vertical partitioning
   - Partition size optimization
   - Query performance implications

2. File System Organization:
   - Hierarchical directory structures
   - Path generation algorithms
   - File naming conventions
   - Metadata storage strategies

3. Query Optimization:
   - Partition pruning (skip irrelevant partitions)
   - Predicate pushdown to partition level
   - Parallel partition scanning
   - Index structures for partitions

4. Retention Management:
   - Time-based data expiration
   - Partition-level deletion
   - Storage lifecycle management
   - Compliance and data governance

Connection to InfluxDB:
- InfluxDB uses shards (time-based partitions)
- Shard duration affects query and write performance
- Retention policies work at shard level
- Compaction operates within shards

Performance Implications:
- More partitions = more files to manage
- Smaller partitions = better query selectivity
- Larger partitions = better compression ratios
- Balance between write efficiency and query speed

Real-World Applications:
- Log file rotation and archival
- Data warehouse partitioning schemes
- Distributed database sharding
- Event stream processing
- IoT data organization

Advanced Topics:
- Adaptive partitioning based on access patterns
- Multi-dimensional partitioning (time + other attributes)
- Partition merging and splitting
- Cross-partition transactions
- Distributed partition management
"""
