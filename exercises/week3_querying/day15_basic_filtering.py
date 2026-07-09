#!/usr/bin/env python3
"""
Day 15: Basic Filtering (the WHERE clause)
==========================================

Problem: The indexes from Week 2 tell you WHICH files/series might match; now you
need to filter individual data points by arbitrary conditions — "field value > 90",
"region = us-west-2 AND status = error". Build a predicate evaluator that supports
comparison operators and boolean AND/OR, then learn *predicate pushdown*: split a
predicate so tag conditions (indexable) run before field conditions (must scan).

Learning Objectives:
- Represent a query condition as data (a Predicate), not code
- Evaluate comparison operators (=, !=, <, <=, >, >=) against a data point
- Compose predicates with boolean AND / OR (short-circuit evaluation)
- Split a compound predicate into a (tag_part, field_part) for pushdown
- Understand why pushing tag filters to the index is a big win

Real-World Connection:
InfluxDB's Flux compiles `filter(fn: (r) => r.region == "us-west-2" and r._value > 90)`
into a predicate tree. The planner pushes the tag portion down to the index (TSI) so
only matching series are read, and applies the field portion during the scan. Same
idea here, just small enough to fit in your head.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


class Op(str, Enum):
    """Comparison operators supported in a WHERE clause."""
    EQ = "="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="


# A data point is the established dict shape:
#   {"measurement": str, "timestamp": float, "tags": {str: str}, "fields": {str: Any}}
Point = Dict[str, Any]


@dataclass
class Comparison:
    """
    A single leaf condition, e.g. `region = "us-west-2"` or `value > 90`.

    `on_tag=True` means `key` refers to point["tags"][key] (always a string);
    `on_tag=False` means point["fields"][key] (any type). This flag is what lets
    the optimizer separate index-able tag conditions from field conditions.
    """
    key: str
    op: Op
    value: Any
    on_tag: bool = False

    def evaluate(self, point: Point) -> bool:
        """
        Return True if `point` satisfies this comparison.

        A missing key evaluates to False for every operator (SQL-ish NULL handling:
        you can't compare against something that isn't there).
        """
        # TODO: pick the right sub-dict (point["tags"] or point["fields"]) from on_tag
        sub_dict = point["tags"] if self.on_tag else point["fields"]

        # TODO: if key is absent -> return False
        if self.key not in sub_dict:
            return False

        # TODO: apply self.op between the point's value and self.value and return the bool
        point_value = sub_dict[self.key]
        if self.op == Op.EQ:
            return point_value == self.value
        elif self.op == Op.NE:
            return point_value != self.value
        elif self.op == Op.LT:
            return point_value < self.value
        elif self.op == Op.LE:
            return point_value <= self.value
        elif self.op == Op.GT:
            return point_value > self.value
        elif self.op == Op.GE:
            return point_value >= self.value
        else:
            raise ValueError(f"Unsupported operator: {self.op}")


class BoolKind(str, Enum):
    AND = "and"
    OR = "or"


@dataclass
class BoolNode:
    """
    An AND / OR of child predicates. Children may be Comparisons or nested BoolNodes,
    so this forms a predicate *tree*.
    """
    kind: BoolKind
    children: List["Predicate"] = field(default_factory=list)

    def evaluate(self, point: Point) -> bool:
        """
        AND -> all children true (short-circuit on first False).
        OR  -> any child true  (short-circuit on first True).
        An empty AND is True; an empty OR is False (standard identities).
        """
        # TODO: implement short-circuit evaluation for both kinds
        if self.kind == BoolKind.AND:
            for child in self.children:
                if not child.evaluate(point):
                    return False
            return True  # all children are True
        elif self.kind == BoolKind.OR:
            for child in self.children:
                if child.evaluate(point):
                    return True
            return False  # all children are False
        else:
            raise ValueError(f"Unsupported BoolKind: {self.kind}")


# A Predicate is either a leaf Comparison or a BoolNode combining predicates.
Predicate = Any  # Union[Comparison, BoolNode]


class FilterEngine:
    """
    Applies a Predicate to a stream of points. Stateless — the predicate is passed
    per call so one engine can serve many queries.
    """

    def apply(self, points: List[Point], predicate: Predicate) -> List[Point]:
        """Return the sublist of points for which predicate.evaluate(point) is True."""
        # TODO: filter points by predicate.evaluate
        return [point for point in points if predicate.evaluate(point)]

    @staticmethod
    def split_for_pushdown(predicate: Predicate) -> Tuple[Optional[Predicate], Optional[Predicate]]:
        """
        Split a top-level AND predicate into (tag_predicate, field_predicate) so the
        tag part can be pushed to the index and the field part applied during scan.

        Rules (keep it simple — only push down the easy, safe case):
        - If `predicate` is an AND node: partition its children into those that are
          *purely tag* conditions and those that touch fields. Return each group
          wrapped back in an AND node (or None if a group is empty).
        - If `predicate` is a single tag Comparison -> (predicate, None).
        - If `predicate` is a single field Comparison -> (None, predicate).
        - Otherwise (e.g. a top-level OR, which can't be safely split) -> (None, predicate).

        A child is "purely tag" if it's a Comparison with on_tag=True. (Nested
        BoolNodes count as non-tag here — we don't recurse; that's a later optimizer's job.)
        """
        # TODO: implement the partition described above
        if isinstance(predicate, Comparison):
            if predicate.on_tag:
                return predicate, None
            else:
                return None, predicate
        elif isinstance(predicate, BoolNode) and predicate.kind == BoolKind.AND:
            tag_children = []
            field_children = []
            for child in predicate.children:
                if isinstance(child, Comparison) and child.on_tag:
                    tag_children.append(child)
                else:
                    field_children.append(child)
            tag_part = BoolNode(BoolKind.AND, tag_children) if tag_children else None
            field_part = BoolNode(BoolKind.AND, field_children) if field_children else None
            return tag_part, field_part
        else:
            # Top-level OR or other non-splittable structure
            return None, predicate


# Convenience constructors so tests read nicely -----------------------------------
def tag(key: str, op: Op, value: str) -> Comparison:
    return Comparison(key=key, op=op, value=value, on_tag=True)


def fld(key: str, op: Op, value: Any) -> Comparison:
    return Comparison(key=key, op=op, value=value, on_tag=False)


def AND(*children: Predicate) -> BoolNode:
    return BoolNode(BoolKind.AND, list(children))


def OR(*children: Predicate) -> BoolNode:
    return BoolNode(BoolKind.OR, list(children))


def _pt(region: str, status: str, value: float, ts: float = 0.0) -> Point:
    return {
        "measurement": "http",
        "timestamp": ts,
        "tags": {"region": region, "status": status},
        "fields": {"value": value},
    }


def test_basic_filtering():
    print("Testing Basic Filtering...")
    engine = FilterEngine()

    points = [
        _pt("us-west-2", "ok", 20.0),
        _pt("us-west-2", "error", 95.0),
        _pt("us-east-1", "ok", 99.0),
        _pt("us-east-1", "error", 10.0),
        _pt("eu-central-1", "ok", 50.0),
    ]

    # Test 1: single tag equality
    res = engine.apply(points, tag("region", Op.EQ, "us-west-2"))
    assert len(res) == 2, f"expected 2 us-west-2 points, got {len(res)}"
    print("✓ Test 1 passed: tag equality")

    # Test 2: field comparison
    res = engine.apply(points, fld("value", Op.GT, 90.0))
    assert {p["fields"]["value"] for p in res} == {95.0, 99.0}
    print("✓ Test 2 passed: field > comparison")

    # Test 3: AND of tag + field
    pred = AND(tag("status", Op.EQ, "error"), fld("value", Op.GE, 90.0))
    res = engine.apply(points, pred)
    assert len(res) == 1 and res[0]["fields"]["value"] == 95.0
    print("✓ Test 3 passed: AND (tag + field)")

    # Test 4: OR
    pred = OR(tag("region", Op.EQ, "eu-central-1"), fld("value", Op.LT, 15.0))
    res = engine.apply(points, pred)
    assert len(res) == 2  # eu point + the value=10 point
    print("✓ Test 4 passed: OR")

    # Test 5: missing key -> False (no crash)
    res = engine.apply(points, fld("nonexistent", Op.GT, 0))
    assert res == []
    print("✓ Test 5 passed: missing key evaluates False")

    # Test 6: nested predicate tree
    pred = AND(
        tag("region", Op.NE, "eu-central-1"),
        OR(fld("value", Op.GT, 90.0), tag("status", Op.EQ, "ok")),
    )
    res = engine.apply(points, pred)
    # region != eu  -> first 4; of those, value>90 (95,99) OR status ok (20,99)
    assert len(res) == 3
    print("✓ Test 6 passed: nested AND/OR tree")

    # Test 7: pushdown split of an AND
    pred = AND(tag("region", Op.EQ, "us-west-2"), fld("value", Op.GT, 90.0))
    tag_part, field_part = FilterEngine.split_for_pushdown(pred)
    assert tag_part is not None and field_part is not None
    # tag_part must match only tag conditions; verify it keeps both us-west points
    assert len(engine.apply(points, tag_part)) == 2
    assert len(engine.apply(points, field_part)) == 2  # the two value>90 points
    # applying both in sequence == applying the original
    combined = engine.apply(engine.apply(points, tag_part), field_part)
    assert combined == engine.apply(points, pred)
    print("✓ Test 7 passed: predicate pushdown split")

    # Test 8: OR can't be split -> everything stays as the field part
    tag_part, field_part = FilterEngine.split_for_pushdown(
        OR(tag("region", Op.EQ, "us-west-2"), fld("value", Op.GT, 90.0))
    )
    assert tag_part is None and field_part is not None
    print("✓ Test 8 passed: top-level OR is not pushed down")

    print("\n🎉 All basic filtering tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement Comparison.evaluate, BoolNode.evaluate, and FilterEngine
       (apply + split_for_pushdown). Remove the `raise NotImplementedError`s.
    2. Run: python day15_basic_filtering.py
    3. All 8 tests should pass.

    Success criteria:
    - Comparisons handle every operator and treat missing keys as False
    - AND/OR short-circuit and honor the empty-node identities
    - split_for_pushdown only splits a safe top-level AND

    Next steps:
    - Day 16: aggregate the points that survive the filter (sum/count/mean/min/max).
    - Think about: why is it unsafe to push down part of an OR to the index?
    """
    test_basic_filtering()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Predicate as Data
   - Representing conditions as a tree of objects (not lambdas) lets the engine
     INSPECT them: reorder, push down, or reject. This is the foundation of every
     query optimizer.

2. Comparison Operators & NULL
   - SQL-style semantics: comparing against a missing value yields "unknown", which
     behaves like False in a WHERE filter. We model that as "missing key -> False".

3. Short-Circuit Boolean Logic
   - AND stops at the first False, OR stops at the first True. Correctness is the
     same either way, but short-circuiting avoids evaluating expensive children.

4. Predicate Pushdown
   - Tag conditions can be answered by the inverted index (Day 8) without reading
     data; field conditions require scanning the point. Splitting an AND lets you
     do the cheap, selective work first. An OR mixes the two, so it generally
     cannot be split without changing results.

Connection to InfluxDB:
- Flux `filter()` builds a predicate the planner rewrites: tag/`_measurement`
  predicates push into the storage read (TSI), field/`_value` predicates run in
  the transformation pipeline. The split you implemented is a miniature of that.

Trade-offs:
- Pushdown reduces I/O dramatically for selective tag filters, but only helps when
  the condition is indexable. Over-eager splitting (e.g. of an OR) produces wrong
  answers — safety first, cleverness second.
"""
