"""
TimeSeriesDB — the product facade
=================================

One class that ties the storage, query-parser, and execution-engine layers into a
simple embedded database: `write(...)` points and `query("SELECT ...")` them back.

    from tsdb import TimeSeriesDB

    db = TimeSeriesDB("data/")
    db.write("cpu", tags={"host": "server1"}, fields={"usage": 75.5})
    db.query("SELECT mean(usage) FROM cpu WHERE host = 'server1'")
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .storage.storage_manager import StorageManagerBuilder
from .server.query_parser import parse_query as _parse_sql
from .server.execution_engine import (
    ExecutionEngine,
    Query as _EngineQuery,
    Condition as _EngineCondition,
)


class TimeSeriesDB:
    """
    Embedded time-series database.

    Args:
        path: directory for on-disk storage (created if missing)
        partition_interval: "1h" | "1d" | "1M" (time partition granularity)
        retention_days: default retention window
        enable_cache / enable_wal: storage-engine toggles
    """

    def __init__(
        self,
        path: str = "data",
        partition_interval: str = "1d",
        retention_days: int = 30,
        enable_cache: bool = True,
        enable_wal: bool = True,
    ):
        self._storage = (
            StorageManagerBuilder()
            .with_path(path)
            .with_partition_interval(partition_interval)
            .with_cache(enable_cache)
            .with_wal(enable_wal)
            .with_retention(retention_days)
            .build()
        )
        if not self._storage.initialize():
            raise RuntimeError(f"failed to initialize storage at {path!r}")

        # The execution engine reads points straight from the storage layer.
        self._engine = ExecutionEngine(read_measurement=self._storage.read_points)

    # ---- writes -----------------------------------------------------------
    def write(
        self,
        measurement: str,
        tags: Dict[str, str],
        fields: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Write a single point. `timestamp` defaults to now. Returns write stats."""
        point = {
            "timestamp": time.time() if timestamp is None else timestamp,
            "tags": tags,
            "fields": fields,
        }
        ok, stats = self._storage.write_points(measurement, [point])
        if not ok:
            raise ValueError(f"write failed: {stats}")
        return stats

    def write_many(self, measurement: str, points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Write many points at once. Each point is {tags, fields, timestamp?}."""
        prepared = [
            {
                "timestamp": p.get("timestamp", time.time()),
                "tags": p.get("tags", {}),
                "fields": p.get("fields", {}),
            }
            for p in points
        ]
        ok, stats = self._storage.write_points(measurement, prepared)
        if not ok:
            raise ValueError(f"write failed: {stats}")
        return stats

    # ---- reads ------------------------------------------------------------
    def query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Run a SQL-like query and return result rows as dicts.

        Example: "SELECT mean(usage) FROM cpu WHERE host = 'server1' GROUP BY region"
        Each row is {<group tag>: <value>, ..., "value": <aggregated value>}.
        Raises ParseError on malformed SQL.
        """
        parsed = _parse_sql(sql)  # parser's Query
        engine_query = _EngineQuery(
            agg=parsed.agg,
            field=parsed.field,
            measurement=parsed.measurement,
            conditions=[
                _EngineCondition(c.key, c.op, c.value, c.is_string)
                for c in parsed.conditions
            ],
            group_by=list(parsed.group_by),
        )
        result = self._engine.execute(engine_query)
        return [{**row.tags, "value": row.value} for row in result.rows]

    def measurements(self) -> List[str]:
        """List all measurements that have data."""
        return self._storage.list_measurements()

    # ---- lifecycle --------------------------------------------------------
    def close(self) -> None:
        """Flush and shut the storage engine down cleanly."""
        self._storage.shutdown()

    def __enter__(self) -> "TimeSeriesDB":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
