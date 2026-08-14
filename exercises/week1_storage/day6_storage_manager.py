#!/usr/bin/env python3
"""
Day 6: Storage Manager
=====================

Problem: Create unified storage interface that coordinates all storage components

Learning Objectives:
- Design clean API interfaces
- Coordinate multiple components (files, partitions, writes, cache)
- Implement configuration management
- Handle component lifecycle and initialization
- Create abstraction layers for complex systems

Real-World Connection:
InfluxDB's storage engine coordinates WAL, cache, TSM files, and compaction.
Understanding how to design and coordinate system components is crucial for
building maintainable and scalable systems.
"""

import os
import json
import time
import shutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Import components from previous exercises
# Note: In real implementation, these would be proper imports
# For this exercise, we'll define interfaces that match what you built


class StorageConfig:
    """Configuration for storage manager."""

    def __init__(
        self,
        base_path: str = "data",
        partition_interval: str = "1d",  # 1h, 1d, 1M
        batch_size: int = 1000,
        enable_wal: bool = True,
        enable_cache: bool = True,
        cache_size: int = 10000,
        cache_flush_interval: int = 30,
        compression_enabled: bool = False,
        retention_days: int = 30,
        max_files_per_partition: int = 100,
    ):
        """Initialize storage configuration with defaults."""
        # TODO: Store all configuration parameters
        if Path(base_path).exists() is False:
            Path(base_path).mkdir(parents=True, exist_ok=True)
        self.base_path = base_path

        # TODO: Validate configuration values
        if not partition_interval or partition_interval not in ["1h", "1d", "1M"]:
            raise ValueError("partition_interval must be one of '1h', '1d', '1M'")
        self.partition_interval = partition_interval

        self.batch_size = batch_size
        self.enable_wal = enable_wal
        self.enable_cache = enable_cache
        self.cache_size = cache_size
        self.cache_flush_interval = cache_flush_interval
        self.compression_enabled = compression_enabled
        self.retention_days = retention_days
        self.max_files_per_partition = max_files_per_partition

        # TODO: Set up derived configurations
        pass

    def validate(self) -> List[str]:
        """
        Validate configuration parameters.

        Returns:
            List of validation error messages (empty if valid)
        """
        # TODO: Validate all configuration parameters
        # TODO: Check for conflicts or invalid combinations
        errors = []
        if self.partition_interval not in ["1h", "1d", "1M"]:
            errors.append("partition_interval must be one of '1h', '1d', '1M'")
        if self.batch_size <= 0:
            errors.append("batch_size must be positive")
        if self.cache_size <= 0:
            errors.append("cache_size must be positive")
        if self.cache_flush_interval <= 0:
            errors.append("cache_flush_interval must be positive")
        if self.retention_days < 0:
            errors.append("retention_days cannot be negative")
        if self.max_files_per_partition <= 0:
            errors.append("max_files_per_partition must be positive")

        # TODO: Return list of errors (empty if valid)
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        # TODO: Convert all config to dictionary
        return {
            "base_path": self.base_path,
            "partition_interval": self.partition_interval,
            "batch_size": self.batch_size,
            "enable_wal": self.enable_wal,
            "enable_cache": self.enable_cache,
            "cache_size": self.cache_size,
            "cache_flush_interval": self.cache_flush_interval,
            "compression_enabled": self.compression_enabled,
            "retention_days": self.retention_days,
            "max_files_per_partition": self.max_files_per_partition,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "StorageConfig":
        """Create configuration from dictionary."""
        # TODO: Create config instance from dictionary
        # TODO: Handle missing keys with defaults
        # we should validate the config after creation
        config = cls(
            base_path=config_dict.get("base_path", "data"),
            partition_interval=config_dict.get("partition_interval", "1d"),
            batch_size=config_dict.get("batch_size", 1000),
            enable_wal=config_dict.get("enable_wal", True),
            enable_cache=config_dict.get("enable_cache", True),
            cache_size=config_dict.get("cache_size", 10000),
            cache_flush_interval=config_dict.get("cache_flush_interval", 30),
            compression_enabled=config_dict.get("compression_enabled", False),
            retention_days=config_dict.get("retention_days", 30),
            max_files_per_partition=config_dict.get("max_files_per_partition", 100),
        )
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {errors}")
        return config


class StorageStats:
    """Statistics about storage system."""

    def __init__(self):
        """Initialize empty statistics."""
        self.points_written = 0
        self.bytes_written = 0
        self.files_created = 0
        self.files_updated = 0
        self.points_read = 0
        self.files_scanned = 0
        self.write_operations = 0
        self.read_operations = 0
        self.total_write_duration = 0.0
        self.total_read_duration = 0.0
        self.last_write_duration = 0.0
        self.last_read_duration = 0.0
        self.last_write_time: Optional[float] = None
        self.last_read_time: Optional[float] = None

    def update_write_stats(
        self, points: int, bytes_written: int, duration: float
    ) -> None:
        """Update statistics from write operation."""
        self.points_written += max(0, points)
        self.bytes_written += max(0, bytes_written)
        self.write_operations += 1
        self.total_write_duration += max(0.0, duration)
        self.last_write_duration = max(0.0, duration)
        self.last_write_time = time.time()

    def update_read_stats(
        self, points_read: int, files_scanned: int, duration: float
    ) -> None:
        """Update statistics from read operation."""
        self.points_read += max(0, points_read)
        self.files_scanned += max(0, files_scanned)
        self.read_operations += 1
        self.total_read_duration += max(0.0, duration)
        self.last_read_duration = max(0.0, duration)
        self.last_read_time = time.time()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total_operations = self.write_operations + self.read_operations
        total_duration = self.total_write_duration + self.total_read_duration

        return {
            "points_written": self.points_written,
            "bytes_written": self.bytes_written,
            "files_created": self.files_created,
            "files_updated": self.files_updated,
            "points_read": self.points_read,
            "files_scanned": self.files_scanned,
            "write_operations": self.write_operations,
            "read_operations": self.read_operations,
            "total_operations": total_operations,
            "total_write_duration": self.total_write_duration,
            "total_read_duration": self.total_read_duration,
            "total_duration": total_duration,
            "average_write_duration": (
                self.total_write_duration / self.write_operations
                if self.write_operations > 0
                else 0.0
            ),
            "average_read_duration": (
                self.total_read_duration / self.read_operations
                if self.read_operations > 0
                else 0.0
            ),
            "write_rate": (
                self.points_written / self.total_write_duration
                if self.total_write_duration > 0
                else 0.0
            ),
            "read_rate": (
                self.points_read / self.total_read_duration
                if self.total_read_duration > 0
                else 0.0
            ),
            "last_write_duration": self.last_write_duration,
            "last_read_duration": self.last_read_duration,
            "last_write_time": self.last_write_time,
            "last_read_time": self.last_read_time,
        }


class StorageManager:
    """
    Main storage manager that coordinates all storage operations.

    Responsibilities:
    - Initialize and manage all storage components
    - Provide unified API for write/read operations
    - Handle configuration and lifecycle management
    - Coordinate between cache, WAL, partitions, and files
    - Manage background tasks (compression, cleanup)
    - Collect and report system statistics
    """

    def __init__(self, config: StorageConfig):
        """
        Initialize storage manager with configuration.

        Args:
            config: Storage configuration
        """

        # TODO: Store configuration
        self.config = config
        self.base_path = Path(config.base_path)
        self.stats = StorageStats()

        # TODO: Set up logging
        self.logger = logging.getLogger(f"{__name__}.StorageManager")
        if not self.logger.handlers:
            self.logger.addHandler(logging.NullHandler())

        self.initialized = False
        self.running = False
        self.shutdown_event = threading.Event()
        self.manager_lock = threading.Lock()

        # TODO: Initialize all storage components
        # Component placeholders; initialize() wires these up later.
        self.writer = None
        self.cache = None
        self.partitioner = None
        self.file_manager = None
        self.index = None

        # TODO: Start background tasks
        self.background_threads: List[threading.Thread] = []

    def initialize(self) -> bool:
        """
        Initialize storage system.

        Returns:
            True if initialization successful, False otherwise

        Initialization Steps:
        1. Validate configuration
        2. Create directory structure
        3. Initialize components (file manager, partitioner, writer, cache)
        4. Replay WAL if enabled
        5. Start background tasks
        6. Load existing metadata
        """

        with self.manager_lock:
            if self.initialized:
                return True

            # TODO: Validate configuration
            validation_errors = self.config.validate()
            if validation_errors:
                self.logger.error(
                    "Storage configuration validation failed: %s", validation_errors
                )
                return False

            # TODO: Create necessary directories
            try:
                self.base_path.mkdir(parents=True, exist_ok=True)
                (self.base_path / "partitions").mkdir(parents=True, exist_ok=True)
                (self.base_path / "metadata").mkdir(parents=True, exist_ok=True)

                if self.config.enable_wal:
                    (self.base_path / "wal").mkdir(parents=True, exist_ok=True)

                if self.config.enable_cache:
                    (self.base_path / "cache").mkdir(parents=True, exist_ok=True)

                # TODO: Initialize all components
                # These are lightweight placeholders until the real component
                # implementations from earlier exercises are wired in.
                self.file_manager = {
                    "base_path": str(self.base_path),
                    "partitions_path": str(self.base_path / "partitions"),
                }
                self.partitioner = {
                    "partition_interval": self.config.partition_interval,
                    "retention_days": self.config.retention_days,
                }
                self.writer = {
                    "batch_size": self.config.batch_size,
                    "enable_wal": self.config.enable_wal,
                }
                self.cache = (
                    {
                        "enabled": True,
                        "size": self.config.cache_size,
                        "flush_interval": self.config.cache_flush_interval,
                    }
                    if self.config.enable_cache
                    else None
                )
                self.index = {
                    "measurements": set(),
                    "tag_keys": {},
                    "tag_values": {},
                    "field_keys": {},
                }

                # TODO: Replay WAL for recovery
                # WAL replay is left as a future integration point because the
                # earlier exercise components are not imported here.

                # TODO: Start background tasks
                self.background_threads = []

                self.initialized = True
                self.running = True
                self.shutdown_event.clear()
                self.logger.info("Storage manager initialized at %s", self.base_path)
                return True
            except Exception as exc:
                self.logger.exception("Failed to initialize storage manager: %s", exc)
                self.initialized = False
                self.running = False
                return False

    def write_points(
        self, measurement: str, points: List[Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Write data points to storage.

        Args:
            measurement: Measurement name
            points: List of data points

        Returns:
            Tuple of (success, statistics)

        Write Flow:
        1. Validate input points
        2. Add to cache if enabled, otherwise write directly
        3. Update indexes
        4. Record statistics
        5. Trigger background tasks if needed
        """
        if not self.initialized or not self.running:
            return False, {"error": "storage manager is not initialized"}

        # TODO: Validate input points
        if not measurement or not isinstance(measurement, str):
            return False, {"error": "measurement must be a non-empty string"}

        if not isinstance(points, list):
            return False, {"error": "points must be a list"}

        valid_points: List[Dict[str, Any]] = []
        invalid_points = 0
        write_started = time.time()

        for point in points:
            if not isinstance(point, dict):
                invalid_points += 1
                continue

            normalized_point = point.copy()
            normalized_point["measurement"] = measurement

            tags = normalized_point.get("tags", {})
            fields = normalized_point.get("fields", {})
            if not isinstance(tags, dict) or not isinstance(fields, dict):
                invalid_points += 1
                continue

            timestamp_value = normalized_point.get("timestamp")
            if timestamp_value is None:
                timestamp_value = time.time()
                normalized_point["timestamp"] = timestamp_value
            elif not isinstance(timestamp_value, (int, float)):
                invalid_points += 1
                continue

            valid_points.append(normalized_point)

        if not valid_points:
            return False, {
                "points_written": 0,
                "points_failed": invalid_points,
                "bytes_written": 0,
                "measurement": measurement,
                "errors": ["no valid points to write"],
            }

        written_files: List[Path] = []
        total_bytes_written = 0

        with self.manager_lock:
            measurement_index = self.index.setdefault("measurements", set())
            tag_key_index = self.index.setdefault("tag_keys", {})
            tag_value_index = self.index.setdefault("tag_values", {})
            field_key_index = self.index.setdefault("field_keys", {})

            measurement_index.add(measurement)
            tag_key_index.setdefault(measurement, set())
            tag_value_index.setdefault(measurement, {})
            field_key_index.setdefault(measurement, {})

            measurement_dir = self.base_path / "partitions" / measurement
            measurement_dir.mkdir(parents=True, exist_ok=True)

            partition_interval = self.config.partition_interval
            partition_groups: Dict[str, List[Dict[str, Any]]] = {}

            for point in valid_points:
                timestamp_value = float(point["timestamp"])
                timestamp_dt = datetime.fromtimestamp(timestamp_value)

                if partition_interval == "1h":
                    partition_key = timestamp_dt.strftime("%Y%m%d_%H")
                elif partition_interval == "1M":
                    partition_key = timestamp_dt.strftime("%Y%m")
                else:
                    partition_key = timestamp_dt.strftime("%Y%m%d")

                partition_groups.setdefault(partition_key, []).append(point)

            for partition_key, partition_points in partition_groups.items():
                partition_path = measurement_dir / f"{partition_key}.jsonl"
                partition_existed = partition_path.exists()

                # TODO: Route through cache or direct write
                try:
                    with open(partition_path, "a", encoding="utf-8") as handle:
                        for point in partition_points:
                            serialized_point = json.dumps(point, sort_keys=True)
                            handle.write(serialized_point + "\n")
                            total_bytes_written += (
                                len(serialized_point.encode("utf-8")) + 1
                            )

                            # TODO: Update indexes and metadata
                            for tag_key, tag_value in point.get("tags", {}).items():
                                tag_key_index[measurement].add(tag_key)
                                tag_value_index[measurement].setdefault(
                                    tag_key, set()
                                ).add(str(tag_value))

                            for field_key in point.get("fields", {}).keys():
                                field_value = point["fields"][field_key]
                                field_key_index[measurement][field_key] = type(
                                    field_value
                                ).__name__

                    written_files.append(partition_path)
                    if not partition_existed:
                        self.stats.files_created += 1
                    else:
                        self.stats.files_updated += 1
                except Exception as exc:
                    self.logger.exception(
                        "Failed to write points for measurement %s partition %s: %s",
                        measurement,
                        partition_key,
                        exc,
                    )
                    return False, {
                        "points_written": 0,
                        "points_failed": len(points),
                        "bytes_written": 0,
                        "measurement": measurement,
                        "errors": [str(exc)],
                    }

            duration = time.time() - write_started
            self.stats.update_write_stats(
                len(valid_points), total_bytes_written, duration
            )

        # TODO: Collect and return statistics
        summary = {
            "measurement": measurement,
            "points_written": len(valid_points),
            "points_failed": invalid_points,
            "bytes_written": total_bytes_written,
            "duration_seconds": time.time() - write_started,
            "files_written": len(written_files),
            "files_created": self.stats.files_created,
            "files_updated": self.stats.files_updated,
        }

        return invalid_points == 0, summary

    def read_points(
        self,
        measurement: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        tag_filters: Optional[Dict[str, str]] = None,
        field_filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read data points from storage.

        Args:
            measurement: Measurement name
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            tag_filters: Tag filter conditions
            field_filters: Field filter conditions
            limit: Maximum number of points to return

        Returns:
            List of matching data points

        Read Flow:
        1. Use indexes to find relevant partitions
        2. Scan partitions in time order
        3. Apply filters during scan
        4. Merge results from multiple partitions
        5. Apply limit and sort final results
        """
        if not self.initialized:
            return []

        # Use indexing to find relevant partitions: one directory per measurement,
        # one JSONL file per time partition (mirrors write_points' layout).
        measurement_dir = self.base_path / "partitions" / measurement
        if not measurement_dir.exists():
            return []

        results: List[Dict[str, Any]] = []
        for partition_path in sorted(measurement_dir.glob("*.jsonl")):
            try:
                with open(partition_path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        point = json.loads(line)

                        # Apply time-range filter (inclusive) during the scan.
                        ts = point.get("timestamp")
                        if start_time is not None and (ts is None or ts < start_time):
                            continue
                        if end_time is not None and (ts is None or ts > end_time):
                            continue

                        # Apply tag filters (all must match; tags compared as strings).
                        if tag_filters:
                            tags = point.get("tags", {})
                            if any(str(tags.get(k)) != str(v)
                                   for k, v in tag_filters.items()):
                                continue

                        # Apply field filters (all must match exactly).
                        if field_filters:
                            fields = point.get("fields", {})
                            if any(fields.get(k) != v
                                   for k, v in field_filters.items()):
                                continue

                        results.append(point)
            except Exception as exc:
                self.logger.exception(
                    "Failed to read partition %s: %s", partition_path, exc
                )
                continue

        # Merge and sort results by timestamp, then apply the limit.
        results.sort(key=lambda p: p.get("timestamp", 0))
        if limit is not None:
            results = results[:limit]
        return results


    def list_measurements(self) -> List[str]:
        """
        List all measurements in storage.

        Returns:
            Sorted list of measurement names
        """
        # Use the in-memory index that write_points maintains.
        return sorted(self.index.get("measurements", set()))

    def list_tag_keys(self, measurement: str) -> List[str]:
        """
        List all tag keys for a measurement.

        Args:
            measurement: Measurement name

        Returns:
            Sorted list of tag keys
        """
        return sorted(self.index.get("tag_keys", {}).get(measurement, set()))

    def list_tag_values(self, measurement: str, tag_key: str) -> List[str]:
        """
        List all values for a specific tag key.

        Args:
            measurement: Measurement name
            tag_key: Tag key name

        Returns:
            Sorted list of tag values
        """
        return sorted(
            self.index.get("tag_values", {}).get(measurement, {}).get(tag_key, set())
        )

    def get_field_keys(self, measurement: str) -> Dict[str, str]:
        """
        Get field keys and their types for a measurement.

        Args:
            measurement: Measurement name

        Returns:
            Dictionary of field_name -> field_type
        """
        return dict(self.index.get("field_keys", {}).get(measurement, {}))

    def get_storage_stats(self) -> StorageStats:
        """
        Get current storage statistics.

        Returns:
            StorageStats object with current statistics
        """
        return self.stats

    def compact_partitions(self, measurement: Optional[str] = None) -> Dict[str, Any]:
        """
        Compact partition files to optimize storage.

        Args:
            measurement: Specific measurement to compact (None for all)

        Returns:
            Compaction statistics

        Compaction Process:
        1. Find partitions that need compaction
        2. Read data from multiple files
        3. Apply compression
        4. Write to new optimized files
        5. Update indexes
        6. Clean up old files
        """
        # TODO: Find partitions needing compaction
        # TODO: Perform compaction with compression
        # TODO: Update indexes after compaction
        # TODO: Return compaction statistics
        pass

    def cleanup_old_data(self, retention_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Clean up data older than retention period.

        Args:
            retention_days: Retention period (uses config default if None)

        Returns:
            Cleanup statistics
        """
        retention = (
            retention_days if retention_days is not None else self.config.retention_days
        )
        cutoff = time.time() - retention * 86400

        partitions_deleted = 0
        bytes_freed = 0
        partitions_root = self.base_path / "partitions"
        if partitions_root.exists():
            for measurement_dir in partitions_root.iterdir():
                if not measurement_dir.is_dir():
                    continue
                for partition_path in measurement_dir.glob("*.jsonl"):
                    # A partition is safe to drop when its NEWEST point is older
                    # than the cutoff (robust regardless of the file naming scheme).
                    max_ts = None
                    try:
                        with open(partition_path, "r", encoding="utf-8") as handle:
                            for line in handle:
                                line = line.strip()
                                if not line:
                                    continue
                                ts = json.loads(line).get("timestamp")
                                if ts is not None and (max_ts is None or ts > max_ts):
                                    max_ts = ts
                    except Exception:
                        continue
                    if max_ts is not None and max_ts < cutoff:
                        bytes_freed += partition_path.stat().st_size
                        partition_path.unlink()
                        partitions_deleted += 1

        return {
            "partitions_deleted": partitions_deleted,
            "files_deleted": partitions_deleted,
            "bytes_freed": bytes_freed,
            "retention_days": retention,
        }

    def backup_metadata(self, backup_path: str) -> bool:
        """
        Backup storage metadata (indexes, configuration, statistics).

        Args:
            backup_path: Path for backup files

        Returns:
            True if backup successful
        """
        # TODO: Backup all metadata to specified path
        # TODO: Include indexes, configuration, statistics
        pass

    def restore_metadata(self, backup_path: str) -> bool:
        """
        Restore storage metadata from backup.

        Args:
            backup_path: Path to backup files

        Returns:
            True if restore successful
        """
        # TODO: Restore metadata from backup
        # TODO: Rebuild indexes if needed
        pass

    def shutdown(self) -> bool:
        """
        Gracefully shutdown storage system.

        Returns:
            True if shutdown successful

        Shutdown Process:
        1. Stop accepting new writes
        2. Flush all caches
        3. Complete background tasks
        4. Close all files
        5. Save metadata
        """
        with self.manager_lock:
            if not self.initialized:
                return True
            # Stop accepting writes, signal background tasks, join threads.
            self.running = False
            self.shutdown_event.set()
            for thread in self.background_threads:
                if thread.is_alive():
                    thread.join(timeout=1.0)
            self.background_threads = []
            self.initialized = False
            self.logger.info("Storage manager shut down cleanly")
            return True

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of storage system.

        Returns:
            Health status and diagnostics

        Health Checks:
        - Disk space availability
        - File system permissions
        - Component status
        - Performance metrics
        - Error rates
        """
        checks: Dict[str, Any] = {}

        # Component status
        checks["initialized"] = self.initialized
        checks["running"] = self.running

        # Storage path reachable + writable
        base_ok = self.base_path.exists() and os.access(self.base_path, os.W_OK)
        checks["storage_path_writable"] = base_ok

        # Disk space availability (best-effort)
        try:
            usage = shutil.disk_usage(self.base_path)
            checks["disk_free_bytes"] = usage.free
        except OSError:
            checks["disk_free_bytes"] = None

        # Overall status: healthy only if initialized, running, and path writable.
        healthy = self.initialized and self.running and base_ok
        return {
            "status": "healthy" if healthy else "unhealthy",
            "checks": checks,
            "measurements": len(self.index.get("measurements", set())),
        }


class StorageManagerBuilder:
    """Builder pattern for creating StorageManager with fluent API."""

    def __init__(self):
        """Initialize builder with default configuration."""
        # Accumulate only the options the caller sets; StorageConfig supplies defaults.
        self._options: Dict[str, Any] = {}

    def with_path(self, path: str) -> "StorageManagerBuilder":
        """Set base storage path."""
        self._options["base_path"] = path
        return self

    def with_partition_interval(self, interval: str) -> "StorageManagerBuilder":
        """Set partition interval (1h, 1d, 1w, 1M)."""
        self._options["partition_interval"] = interval
        return self

    def with_cache(
        self, enabled: bool = True, size: int = 10000
    ) -> "StorageManagerBuilder":
        """Configure write cache."""
        self._options["enable_cache"] = enabled
        self._options["cache_size"] = size
        return self

    def with_wal(self, enabled: bool = True) -> "StorageManagerBuilder":
        """Configure write-ahead logging."""
        self._options["enable_wal"] = enabled
        return self

    def with_compression(self, enabled: bool = True) -> "StorageManagerBuilder":
        """Configure compression."""
        self._options["compression_enabled"] = enabled
        return self

    def with_retention(self, days: int) -> "StorageManagerBuilder":
        """Set data retention period."""
        self._options["retention_days"] = days
        return self

    def build(self) -> StorageManager:
        """Build StorageManager with configured options."""
        return StorageManager(StorageConfig(**self._options))


def test_storage_manager():
    """
    Test cases for storage manager.
    """
    print("Testing Storage Manager...")

    # Setup test environment
    import tempfile
    import shutil

    test_dir = tempfile.mkdtemp()

    try:
        # Test 1: Builder pattern and initialization
        storage_manager = (
            StorageManagerBuilder()
            .with_path(test_dir)
            .with_partition_interval("1d")
            .with_cache(True, 1000)
            .with_wal(True)
            .with_retention(30)
            .build()
        )

        success = storage_manager.initialize()
        assert success, "Storage manager should initialize successfully"
        print("✓ Test 1 passed: Builder pattern and initialization")

        # Test 2: Write operations
        # Generate test data
        test_points = []
        base_timestamp = time.time()

        for i in range(100):
            point = {
                "timestamp": base_timestamp + i * 60,  # 1-minute intervals
                "tags": {
                    "host": f"server{i % 5}",
                    "region": "us-west",
                    "environment": "test",
                },
                "fields": {
                    "cpu_usage": 50.0 + (i % 30),
                    "memory_mb": 1000 + i * 10,
                    "online": True,
                },
            }
            test_points.append(point)

        success, stats = storage_manager.write_points("system_metrics", test_points)
        assert success, f"Write should succeed, got stats: {stats}"
        print("✓ Test 2 passed: Write operations")

        # Test 3: Read operations
        # Read all points
        all_points = storage_manager.read_points("system_metrics")
        assert (
            len(all_points) >= 100
        ), f"Should read at least 100 points, got {len(all_points)}"

        # Read with time range
        start_time = base_timestamp
        end_time = base_timestamp + 3600  # 1 hour
        time_filtered = storage_manager.read_points(
            "system_metrics", start_time=start_time, end_time=end_time
        )
        assert len(time_filtered) > 0, "Should find points in time range"
        assert len(time_filtered) <= len(
            all_points
        ), "Time filter should reduce results"

        # Read with tag filters
        tag_filtered = storage_manager.read_points(
            "system_metrics", tag_filters={"host": "server1", "region": "us-west"}
        )
        assert len(tag_filtered) > 0, "Should find points matching tag filters"

        # Read with limit
        limited = storage_manager.read_points("system_metrics", limit=10)
        assert (
            len(limited) == 10
        ), f"Should return exactly 10 points, got {len(limited)}"
        print("✓ Test 3 passed: Read operations with filters")

        # Test 4: Metadata operations
        measurements = storage_manager.list_measurements()
        assert (
            "system_metrics" in measurements
        ), "Should find system_metrics measurement"

        tag_keys = storage_manager.list_tag_keys("system_metrics")
        expected_tags = ["host", "region", "environment"]
        for tag in expected_tags:
            assert tag in tag_keys, f"Should find tag key: {tag}"

        tag_values = storage_manager.list_tag_values("system_metrics", "host")
        assert len(tag_values) > 0, "Should find tag values for host"

        field_keys = storage_manager.get_field_keys("system_metrics")
        expected_fields = ["cpu_usage", "memory_mb", "online"]
        for field in expected_fields:
            assert field in field_keys, f"Should find field key: {field}"
        print("✓ Test 4 passed: Metadata operations")

        # Test 5: Statistics
        stats = storage_manager.get_storage_stats()
        assert isinstance(stats, StorageStats), "Should return StorageStats object"

        summary = stats.get_summary()
        assert isinstance(summary, dict), "Should return statistics dictionary"
        assert "points_written" in summary, "Should include write statistics"
        print("✓ Test 5 passed: Statistics collection")

        # Test 6: Health check
        health = storage_manager.health_check()
        assert isinstance(health, dict), "Should return health status dictionary"
        assert "status" in health, "Should include overall status"
        print("✓ Test 6 passed: Health check")

        # Test 7: Cleanup operations (optional - may not be fully implemented)
        try:
            cleanup_stats = storage_manager.cleanup_old_data(
                retention_days=1000
            )  # Don't delete our test data
            assert isinstance(cleanup_stats, dict), "Should return cleanup statistics"
            print("✓ Test 7 passed: Cleanup operations")
        except NotImplementedError:
            print("⚠️  Test 7 skipped: Cleanup not implemented yet")

        # Test 8: Graceful shutdown
        success = storage_manager.shutdown()
        assert success, "Storage manager should shutdown gracefully"
        print("✓ Test 8 passed: Graceful shutdown")

        print("\n🎉 All storage manager tests passed!")
        print("Your storage manager correctly provides:")
        print("  - Unified API for all storage operations")
        print("  - Configuration management and validation")
        print("  - Component coordination and lifecycle management")
        print("  - Statistics collection and health monitoring")
        print("  - Graceful initialization and shutdown")

    finally:
        # Cleanup test directory
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    """
    Instructions:
    1. Implement all TODO methods in StorageManager, StorageConfig, and StorageManagerBuilder classes
    2. Integrate components from previous exercises (FileManager, TimePartitioner, BatchWriter)
    3. Run this file to test: python day6_storage_manager.py
    4. All tests should pass

    Success criteria:
    - All 8 tests pass
    - Clean API that hides complexity of individual components
    - Proper configuration management
    - Statistics collection works
    - Health checks provide useful information
    - Graceful shutdown completes all operations

    Next steps:
    - Move to day7_compression.py
    - Think about: How would you handle schema evolution?
    - Consider: What monitoring and alerting would be needed in production?
    """
    test_storage_manager()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts Learned:

1. System Architecture Patterns:
   - Facade pattern (StorageManager hides complexity)
   - Builder pattern (fluent configuration API)
   - Component coordination and lifecycle management
   - Separation of concerns between components

2. API Design Principles:
   - Clean, intuitive interfaces
   - Consistent error handling
   - Comprehensive configuration options
   - Statistics and observability built-in

3. Configuration Management:
   - Validation and default values
   - Serialization for persistence
   - Runtime reconfiguration considerations
   - Environment-specific overrides

4. System Observability:
   - Statistics collection at all levels
   - Health checks for proactive monitoring
   - Performance metrics and benchmarking
   - Diagnostic information for troubleshooting

Connection to InfluxDB:
- InfluxDB Engine coordinates WAL, Cache, TSM, and Compaction
- Clean APIs enable different storage backends
- Configuration management handles complex deployments
- Observability is critical for production systems

Software Engineering Principles:
- Abstraction layers hide implementation complexity
- Interface segregation keeps APIs focused
- Dependency injection enables testing and flexibility
- Error handling provides clear failure modes

Real-World Applications:
- Database storage engines
- Message queue implementations
- File system abstractions
- Cloud storage services
- Data pipeline orchestration

Production Considerations:
- Resource management (memory, file handles, threads)
- Graceful degradation under load
- Configuration hot reloading
- Metrics export for monitoring systems
- Backup and disaster recovery procedures
"""
