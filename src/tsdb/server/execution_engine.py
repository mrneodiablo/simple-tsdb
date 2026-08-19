#!/usr/bin/env python3

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# Local AST mirror of Day 24's output (kept local so this exercise tests standalone).
@dataclass
class Condition:
    key: str
    op: str
    value: Any
    is_string: bool = False


@dataclass
class Query:
    agg: str
    field: str
    measurement: str
    conditions: List[Condition] = field(default_factory=list)  # AND-joined
    group_by: List[str] = field(default_factory=list)


@dataclass
class Row:
    """One result row: the group's tag values + the aggregated value."""
    tags: Dict[str, str]
    value: Optional[float]


@dataclass
class ResultSet:
    agg: str
    field: str
    rows: List[Row] = field(default_factory=list)


_OPS = {
    "=":  lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# read_measurement: measurement name -> list of point dicts (the Week 1 shape).
ReadFn = Callable[[str], List[Dict[str, Any]]]


class ExecutionEngine:
    """
    Executes a Query AST against an injected data source.

    Dependency injected:
      - read_measurement(name) -> list of points  (fake in tests; IndexedReader in lab)
    """

    def __init__(self, read_measurement: ReadFn):
        self.read = read_measurement

    def _match(self, point: Dict[str, Any], cond: Condition) -> bool:
        """
        True if `point` satisfies `cond`. Resolve cond.key against tags first, then
        fields. A missing key -> False (SQL-ish null semantics, like Day 15).
        """
        # TODO: find the value in point["tags"] or point["fields"] (False if absent);
        #       apply _OPS[cond.op] between the point's value and cond.value.

        if cond.key in point["tags"]:
            point_value = point["tags"][cond.key]
        elif cond.key in point["fields"]:
            point_value = point["fields"][cond.key]
        else:
            return False  # Key not found in tags or fields
        return _OPS[cond.op](point_value, cond.value)
        

    def _aggregate(self, values: List[Any], agg: str) -> Optional[float]:
        """
        Aggregate a list of raw field values with the named function.
        - Ignore non-numeric / None values (null handling).
        - "count" returns the count of numeric values (0 is valid, not None).
        - sum/mean/min/max return None when there are no numeric values.
        - Raise ValueError for an unknown agg name.
        """
        # TODO: filter to numerics; handle count specially; dispatch sum/mean/min/max.
        numeric_values = [v for v in values if _is_num(v)]
        if agg == "count":
            return len(numeric_values)
        if not numeric_values:
            return None
        if agg == "sum":
            return sum(numeric_values)
        if agg == "mean":
            return sum(numeric_values) / len(numeric_values)
        if agg == "min":
            return min(numeric_values)
        if agg == "max":
            return max(numeric_values)
        raise ValueError(f"Unknown aggregation: {agg}")

    def execute(self, query: Query) -> ResultSet:
        """
        Run the pipeline:
          1. points = self.read(query.measurement)
          2. filter: keep points satisfying ALL conditions (AND)
          3. group: key each point by tuple(point["tags"].get(t) for t in group_by);
             empty group_by -> a single global group with key ()
          4. aggregate query.field per group
          5. build Rows (tags dict from the group key) sorted by the key; return ResultSet

        With no group_by, always return exactly one Row (tags={}), even if no points
        matched (value follows _aggregate's empty semantics).
        """
        # TODO: implement the 5-step pipeline described above.
        # Step 1: Read points
        points = self.read(query.measurement)

        # Step 2: Filter points based on conditions
        filtered_points = []

        for point in points:
            for cond in query.conditions:
                if not self._match(point, cond):
                    break  # If any condition fails, skip this point
            else:
                filtered_points.append(point)  # All conditions passed

        # Step 3: Group points
        groups: Dict[Tuple[Optional[str], ...], List[Dict[str, Any]]] = {}
        if query.group_by:
            for point in filtered_points:
                group_key = tuple(point["tags"].get(tag) for tag in query.group_by)
                groups.setdefault(group_key, []).append(point)
        else:
            groups[()] = filtered_points  # Single global group

        # Step 4: Aggregate per group
        rows: List[Row] = []
        for group_key, group_points in groups.items():
            field_values = [point["fields"].get(query.field) for point in group_points]
            agg_value = self._aggregate(field_values, query.agg)
            tags_dict = {tag: value for tag, value in zip(query.group_by, group_key) if value is not None}
            rows.append(Row(tags=tags_dict, value=agg_value))

        # Step 5: Sort rows by group key
        rows.sort(key=lambda r: tuple(r.tags.get(tag) for tag in query.group_by))
        return ResultSet(agg=query.agg, field=query.field, rows=rows) 

