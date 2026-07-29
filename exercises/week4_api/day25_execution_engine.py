#!/usr/bin/env python3
"""
Day 25: Query Execution Engine (bind the AST to data + operators)
================================================================

Problem: Day 24 gives you a Query AST; now RUN it. The execution engine is the glue
of the whole project: it reads points (Week 1/2 storage + indexes), filters them
(Week 3 Day 15), groups them (Day 19), and aggregates each group (Day 16) — then
returns a tidy result set. Here you wire those stages together behind one execute()
call, with the data source injected so it tests against in-memory fakes.

Learning Objectives:
- Turn a declarative Query into an imperative pipeline (read -> filter -> group -> agg)
- Resolve a condition's key to a tag or field at run time
- Group by tag values and aggregate a field per group
- Shape results into a stable, sorted ResultSet
- Inject the data source so the engine is testable without storage/indexes

Real-World Connection:
This is InfluxDB's query executor in miniature: the planner's AST drives reads from the
storage engine, predicates filter, and reducers aggregate per group/series. The
injected `read_measurement` stands in for the Week 2 IndexedReader you'd wire in the lab.
"""

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


# ---------------------------------------------------------------------------
# Fakes for testing
# ---------------------------------------------------------------------------
def make_reader(points_by_measurement: Dict[str, List[Dict[str, Any]]]) -> ReadFn:
    """Build a read_measurement fn backed by an in-memory dict (unknown -> [])."""
    return lambda name: list(points_by_measurement.get(name, []))


def _pt(measurement: str, tags: Dict[str, str], value: float) -> Dict[str, Any]:
    return {"measurement": measurement, "timestamp": 0.0, "tags": tags, "fields": {"value": value}}


def test_execution_engine():
    print("Testing Query Execution Engine...")

    points = {
        "cpu": [
            _pt("cpu", {"host": "a", "region": "us"}, 10),
            _pt("cpu", {"host": "a", "region": "us"}, 30),
            _pt("cpu", {"host": "b", "region": "us"}, 100),
            _pt("cpu", {"host": "c", "region": "eu"}, 50),
        ]
    }
    engine = ExecutionEngine(make_reader(points))

    # Test 1: global mean, no filter/group
    rs = engine.execute(Query(agg="mean", field="value", measurement="cpu"))
    assert len(rs.rows) == 1 and rs.rows[0].tags == {}
    assert rs.rows[0].value == 47.5   # (10+30+100+50)/4
    print("✓ Test 1 passed: global mean")

    # Test 2: WHERE tag filter
    rs = engine.execute(Query("sum", "value", "cpu",
                              conditions=[Condition("region", "=", "us", is_string=True)]))
    assert rs.rows[0].value == 140   # 10+30+100
    print("✓ Test 2 passed: WHERE tag filter")

    # Test 3: WHERE field filter (numeric)
    rs = engine.execute(Query("count", "value", "cpu",
                              conditions=[Condition("value", ">", 25)]))
    assert rs.rows[0].value == 3   # 30, 100, 50
    print("✓ Test 3 passed: WHERE field filter")

    # Test 4: GROUP BY host
    rs = engine.execute(Query("mean", "value", "cpu", group_by=["host"]))
    by = {tuple(sorted(r.tags.items())): r.value for r in rs.rows}
    assert by[(("host", "a"),)] == 20   # (10+30)/2
    assert by[(("host", "b"),)] == 100
    assert by[(("host", "c"),)] == 50
    print("✓ Test 4 passed: GROUP BY host")

    # Test 5: multiple AND conditions
    rs = engine.execute(Query("max", "value", "cpu", conditions=[
        Condition("region", "=", "us", is_string=True),
        Condition("value", "<", 100),
    ]))
    assert rs.rows[0].value == 30
    print("✓ Test 5 passed: AND conditions")

    # Test 6: rows sorted deterministically by group key
    rs = engine.execute(Query("sum", "value", "cpu", group_by=["host"]))
    keys = [tuple(sorted(r.tags.items())) for r in rs.rows]
    assert keys == sorted(keys)
    print("✓ Test 6 passed: deterministic row order")

    # Test 7: empty measurement -> single global row, count 0 / mean None
    empty = ExecutionEngine(make_reader({}))
    assert empty.execute(Query("count", "value", "cpu")).rows[0].value == 0
    assert empty.execute(Query("mean", "value", "cpu")).rows[0].value is None
    print("✓ Test 7 passed: empty measurement semantics")

    # Test 8: unknown agg raises ValueError
    try:
        engine.execute(Query("median", "value", "cpu"))
        assert False, "expected ValueError for unknown agg"
    except ValueError:
        pass
    print("✓ Test 8 passed: unknown agg rejected")

    print("\n🎉 All execution engine tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement ExecutionEngine._match, _aggregate, and execute.
    2. Run: python day25_execution_engine.py
    3. All 8 tests should pass.

    Success criteria:
    - execute() runs read -> filter -> group -> aggregate correctly
    - Conditions resolve to tags or fields; missing keys drop the point
    - No group_by yields one global row; GROUP BY yields one row per group, sorted
    - count vs sum/mean/min/max honor the empty-input semantics from Day 16

    Next steps:
    - Day 26: a client that sends queries and formats these ResultSets for humans.
    - Think about: where would you wire the real Week 2 IndexedReader to prune reads
      before filtering? (Hint: predicate pushdown — Day 15 / Day 20.)
    """
    test_execution_engine()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Declarative -> Imperative
   - The AST says WHAT the user wants; the engine decides HOW: which points to read,
     in what order to filter/group/aggregate. This separation is why the same query
     can be optimized (Day 20) without changing its meaning.

2. Runtime Key Resolution
   - A parsed condition doesn't know if `region` is a tag or `value` is a field. The
     engine resolves it against the point at run time (tags first, then fields),
     mirroring how the schema-less data model treats them differently.

3. Group-Then-Reduce
   - Reuses Day 19's hash grouping and Day 16's aggregators: partition by the group
     key, fold each partition. The engine is mostly plumbing between components you
     already built — the payoff of sequential, composable design.

4. Dependency Injection at the Boundary
   - read_measurement is the seam between the query layer and the storage/index layer.
     Injecting it lets you test the executor with fakes now and drop in the real
     IndexedReader in the lab without touching engine code.

Connection to InfluxDB:
- The executor walks the planned AST, pulls series from the storage engine (with
  pushed-down predicates and time bounds), and applies transformations/reducers per
  group — the same read -> filter -> group -> aggregate shape you implemented.

Trade-offs:
- This engine reads ALL points for a measurement then filters in memory (simple, but
  scans everything). The real win is pushing tag predicates + time ranges into the
  read (Week 2) so far fewer points are ever materialized — the optimization the lab
  and Day 20 point toward.
"""
