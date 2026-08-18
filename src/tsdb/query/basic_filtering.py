#!/usr/bin/env python3

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
