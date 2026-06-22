#!/usr/bin/env python3
"""
Day 1: File Operations & Data Structures
========================================

Problem: Implement basic file operations for time-series data storage

Learning Objectives:
- Understand file I/O operations in Python
- Design directory structure for time-series data
- Handle file operation errors gracefully
- Create foundation for data persistence

Real-World Connection:
InfluxDB organizes data in directories like:
/var/lib/influxdb2/engine/data/ORG_ID/BUCKET_ID/autogen/SHARD_ID/

Your task is to create a simpler but similar structure.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path


class FileManager:
    """
    Manages file operations for time-series database storage.

    Directory structure:
    data/
    ├── 2025/
    │   ├── 01/
    │   │   ├── 01/
    │   │   │   ├── cpu_metrics.json
    │   │   │   └── memory_metrics.json
    │   │   └── 02/
    │   └── 02/

    Requirements:
    1. Create hierarchical directory structure by year/month/day
    2. Store different measurements in separate files
    3. Handle concurrent access safely
    4. Provide atomic write operations
    5. Implement error recovery
    """

    def __init__(self, base_path: str = "data"):
        """Initialize file manager with base storage path."""
        # TODO: Initialize the file manager
        # Hint: Store base_path and ensure it exists
        self.base_path = Path(base_path)

    def get_file_path(self, measurement: str, timestamp: float) -> Path:
        """
        Generate file path for a measurement at given timestamp.

        Args:
            measurement: Name of the measurement (e.g., "cpu", "memory")
            timestamp: Unix timestamp

        Returns:
            Path object pointing to the data file

        Example:
            timestamp=1672531200 (2023-01-01 00:00:00)
            measurement="cpu"
            -> Path("data/2023/01/01/cpu_metrics.json")
        """
        # TODO: Convert timestamp to datetime
        current_time = datetime.fromtimestamp(timestamp)
        year = current_time.strftime("%Y")
        month = current_time.strftime("%m")
        day = current_time.strftime("%d")

        # TODO: Create year/month/day directory structure
        dir_path_measurement = self.base_path / year / month / day
        dir_path_measurement.mkdir(parents=True, exist_ok=True)

        # TODO: Return path with measurement name
        return dir_path_measurement / f"{measurement}_metrics.json"

    def ensure_directory_exists(self, file_path: Path) -> None:
        """
        Ensure all parent directories exist for the given file path.

        Args:
            file_path: Path to the file

        Requirements:
        - Create parent directories if they don't exist
        - Handle permission errors gracefully
        - Use atomic directory creation (no race conditions)
        """
        # TODO: Create parent directories
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    def write_data_point(self, measurement: str, data: Dict[str, Any]) -> bool:
        """
        Write a single data point to appropriate file.

        Args:
            measurement: Measurement name
            data: Data point with timestamp and fields

        Returns:
            True if write successful, False otherwise

        Requirements:
        - Append to existing file or create new one
        - Use atomic write operation (tmp file + rename)
        - Handle concurrent writes safely
        - Return success/failure status

        Data format in file:
        {"timestamp": 1672531200, "tags": {"host": "server1"}, "fields": {"cpu": 80.5}}
        """
        # TODO: Get file path for this measurement and timestamp

        # if "timestamp" not in data then use current time
        measurement_time = data.get("timestamp", time.time())
        file_path = self.get_file_path(measurement, timestamp=measurement_time)

        # TODO: Ensure directory exists
        self.ensure_directory_exists(file_path)

        # TODO: Read existing data (if file exists)
        existing_data = []
        if file_path.exists():
            with open(file_path, "r") as f:
                for line in f:
                    existing_data.append(json.loads(line))

        # TODO: Append new data point
        existing_data.append(data)

        # TODO: Write atomically (tmp file + rename)

        # write to temp file first
        # writing to a temp file ensures that if the process crashes
        # during the write, the original file remains intact
        # there are some solution for full atomic write like using file locks
        # but in this version we will use simple tmp file + rename approach: minimize complexity
        # but still provide some small level of atomicity
        temp_file_path = file_path.with_suffix(".tmp")
        try:
            with open(temp_file_path, "w") as temp_file:
                for point in existing_data:
                    temp_file.write(json.dumps(point) + "\n")
            # rename temp file to actual file (atomic operation),
            # this systemcall OS responsible for atomicity
            os.replace(temp_file_path, file_path)
            return True
        except Exception as e:
            print(f"Error writing data point: {e}")
            return False

    def read_data_points(
        self, measurement: str, start_time: float, end_time: float
    ) -> List[Dict[str, Any]]:
        """
        Read data points from files within time range.

        Args:
            measurement: Measurement name
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)

        Returns:
            List of data points sorted by timestamp

        Requirements:
        - Scan all relevant files in time range
        - Filter data points by timestamp
        - Sort results by timestamp
        - Handle missing files gracefully
        """
        # TODO: Determine which files might contain data in time range
        # since files are organized by day, we can calculate which days to check
        # then read those files and filter points by time range

        # Initialize empty list for results
        points = []
        start_dt = datetime.fromtimestamp(start_time)
        end_dt = datetime.fromtimestamp(end_time)

        current_dt = start_dt
        while current_dt <= end_dt:
            year = current_dt.strftime("%Y")  # [0000-9999]
            month = current_dt.strftime("%m")  # [01-12]
            day = current_dt.strftime("%d")  # [01-31]
            file_path = (
                self.base_path / year / month / day / f"{measurement}_metrics.json"
            )

            # TODO: Read and parse each file
            if file_path.exists():
                with open(file_path, "r") as f:
                    for line in f:
                        point = json.loads(line)

                        # TODO: Filter points by time range
                        point_time = point.get("timestamp", 0)
                        if start_time <= point_time <= end_time:
                            points.append(point)
            # Move to next day
            current_dt += timedelta(days=1)

        # TODO: Sort by timestamp
        points.sort(key=lambda x: x.get("timestamp", 0))
        return points

    def list_measurements(self) -> List[str]:
        """
        List all measurement names found in storage.

        Returns:
            Sorted list of unique measurement names

        Requirements:
        - Scan all files in all directories
        - Extract measurement names from filenames
        - Return unique, sorted list
        """
        # TODO: Walk through all directories
        mesasurements = set()

        # TODO: walk all files and find those match pattern *_metrics.json
        for file_path in self.base_path.rglob("*_metrics.json"):
            measurement_name = file_path.stem.replace("_metrics", "")
            mesasurements.add(measurement_name)

        # TODO: Return unique sorted list
        return sorted(mesasurements)

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary with statistics:
            - total_files: Number of data files
            - total_size_bytes: Total storage size
            - measurements_count: Number of different measurements
            - oldest_timestamp: Earliest data point timestamp
            - newest_timestamp: Latest data point timestamp
        """
        # init stats dictionary
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "measurements_count": 0,
            "oldest_timestamp": None,
            "newest_timestamp": None,
        }

        # Collect all day directories (YYYY/MM/DD structure)
        day_dirs = set()

        # TODO: Walk through all files
        for file_path in self.base_path.rglob("*_metrics.json"):
            stats["total_files"] += 1

            # TODO: Calculate file count and total size
            stats["total_size_bytes"] += file_path.stat().st_size

            # TODO: Find min/max timestamps
            # to mitigate full scan of all data points,
            # we get min timestamps by get file in oldest directory (since structure of data organize by year/month/day), check first lines of files in that directory
            # similarly for max timestamps, we check latest modified file and last lines of files in that directory
            # this is an approximation, not exact min/max across all data points
            # but should be sufficient for basic stats
            day_dir = file_path.parent
            # Validate it's a day directory (has year/month/day structure)
            parts = day_dir.relative_to(self.base_path).parts
            if len(parts) == 3:  # Expecting YYYY/MM/DD structure
                day_dirs.add(day_dir)

        all_dirs = sorted(day_dirs)
        if all_dirs:
            # oldest directory
            oldest_dir = all_dirs[0]
            for file_path in oldest_dir.glob("*_metrics.json"):
                with open(file_path, "r") as f:
                    first_line = f.readline()
                    if first_line:
                        point = json.loads(first_line)
                        ts = point.get("timestamp", None)
                        if ts is not None:
                            if (
                                stats["oldest_timestamp"] is None
                                or ts < stats["oldest_timestamp"]
                            ):
                                stats["oldest_timestamp"] = ts

            # newest directory
            newest_dir = all_dirs[-1]
            for file_path in newest_dir.glob("*_metrics.json"):
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1]
                        point = json.loads(last_line)
                        ts = point.get("timestamp", None)
                        if ts is not None:
                            if (
                                stats["newest_timestamp"] is None
                                or ts > stats["newest_timestamp"]
                            ):
                                stats["newest_timestamp"] = ts

        # TODO: Count unique measurements
        stats["measurements_count"] = len(self.list_measurements())

        return stats


def test_file_manager():
    """
    Test cases for FileManager class.

    This is your verification that the implementation works correctly.
    Run this to check your solution.
    """
    # Cleanup test directory
    import shutil

    test_dir = "test_data"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    fm = FileManager(test_dir)

    # Test 1: Write single data point
    timestamp = time.time()
    data = {
        "timestamp": timestamp,
        "tags": {"host": "server1", "region": "us-west"},
        "fields": {"cpu_usage": 75.5, "memory_usage": 60.2},
    }

    result = fm.write_data_point("cpu", data)
    assert result == True, "Write should succeed"
    print("✓ Test 1 passed: Single data point write")

    # Test 2: Read data back
    points = fm.read_data_points("cpu", timestamp - 1, timestamp + 1)
    assert len(points) == 1, f"Should read 1 point, got {len(points)}"
    assert points[0]["fields"]["cpu_usage"] == 75.5, "Should read correct data"
    print("✓ Test 2 passed: Data point read")

    # Test 3: Write multiple points to different measurements
    timestamp2 = timestamp + 60  # 1 minute later
    memory_data = {
        "timestamp": timestamp2,
        "tags": {"host": "server2"},
        "fields": {"available_mb": 1024, "used_mb": 512},
    }

    fm.write_data_point("memory", memory_data)
    measurements = fm.list_measurements()
    assert "cpu" in measurements, "Should find cpu_metrics"
    assert "memory" in measurements, "Should find memory_metrics"
    print("✓ Test 3 passed: Multiple measurements")

    # Test 4: Storage stats
    stats = fm.get_storage_stats()
    print(stats)
    assert (
        stats["total_files"] >= 2
    ), f"Should have at least 2 files, got {stats['total_files']}"
    assert (
        stats["measurements_count"] == 2
    ), f"Should have 2 measurements, got {stats['measurements_count']}"
    print("✓ Test 4 passed: Storage statistics")

    # Test 5: Time range queries
    points = fm.read_data_points("cpu", 0, timestamp - 1)
    assert len(points) == 0, "Should not find points outside time range"

    points = fm.read_data_points("cpu", timestamp, timestamp + 3600)
    assert len(points) == 1, "Should find points in time range"
    print("✓ Test 5 passed: Time range queries")

    print("\n🎉 All tests passed! Your file manager works correctly.")
    print(f"Check the '{test_dir}' directory to see the file structure created.")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement all the TODO methods in the FileManager class
    2. Run this file to test your implementation: python day1_file_operations.py
    3. All tests should pass
    4. Examine the created directory structure

    Success criteria:
    - All 5 tests pass
    - Directory structure follows year/month/day pattern
    - Files contain valid JSON data
    - Concurrent access is handled safely (atomic writes)

    Next steps:
    - Move to day2_serialization.py
    - Think about: How could this scale to millions of data points?
    - Consider: What happens if the system crashes during a write?
    """
    test_file_manager()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts Learned:

1. File System Organization:
   - Hierarchical directory structure for time-series data
   - Separation by measurement type
   - Time-based partitioning for efficient queries

2. Atomic Operations:
   - Write to temporary file then rename (atomic on most filesystems)
   - Prevents corruption during concurrent access
   - Essential for database reliability

3. Error Handling:
   - Graceful handling of missing files/directories
   - Permission and I/O error recovery
   - Defensive programming practices

4. Storage Design Patterns:
   - Append-only writes for time-series data
   - Directory structure that scales with time
   - Separation of concerns (measurements in different files)

Connection to InfluxDB:
- InfluxDB uses similar time-based directory structures
- TSM files are organized by shard (time ranges)
- Atomic writes ensure data consistency
- Directory layout optimizes for time-range queries

Performance Considerations:
- File per measurement per day balances file size and I/O
- Directory structure enables efficient time range scans
- Atomic writes add overhead but ensure consistency

Real-World Applications:
- Log file rotation systems
- Time-series data collection (metrics, IoT sensors)
- Event storage systems
- Data warehousing with time partitions
"""
