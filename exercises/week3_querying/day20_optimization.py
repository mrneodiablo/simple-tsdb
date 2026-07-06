#!/usr/bin/env python3
"""
Day 20: Query Optimization (execution plans & operation reordering)
==================================================================

Problem: A query is a pipeline of stages — filter, group, aggregate, limit. Run
naively, you might aggregate a million points and then throw most away. An optimizer
reorders and rewrites the pipeline so the cheapest, most selective work happens
first: push filters ahead of aggregation, push tag filters into the index, apply
LIMIT early where it's safe. You build a tiny rule-based optimizer over a plan.

Learning Objectives:
- Model a query as an ordered list of stage objects (a logical plan)
- Estimate selectivity/cost to compare plans
- Apply rewrite rules: filter pushdown, redundant-stage elimination, limit pushdown
- Understand which reorderings preserve results and which don't
- Produce an optimized plan + a human-readable EXPLAIN

Real-World Connection:
Every database has a planner. InfluxDB's storage layer pushes predicate + time
bounds down to the read; Flux rewrites `filter |> filter` into one filter and pushes
it before `map`. This is a rule-based (heuristic) optimizer, the same family as
Postgres's early rewrite phase — before cost-based join ordering.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class StageType(str, Enum):
    SCAN = "scan"          # read points (optionally with a pushed-down tag predicate)
    FILTER = "filter"      # apply a predicate to the stream
    GROUP = "group"        # partition by tags
    AGGREGATE = "aggregate"
    LIMIT = "limit"


@dataclass
class Stage:
    """
    One pipeline stage. `on_tag` marks a FILTER as a pure-tag predicate (index-able,
    so it can be pushed into the SCAN). `selectivity` in [0,1] estimates the fraction
    of rows that survive (lower = more selective = cheaper downstream).
    """
    type: StageType
    on_tag: bool = False
    selectivity: float = 1.0
    limit: Optional[int] = None
    detail: str = ""

    def __repr__(self) -> str:
        extra = ""
        if self.type == StageType.FILTER:
            extra = f"[{'tag' if self.on_tag else 'field'}, sel={self.selectivity}]"
        if self.type == StageType.LIMIT:
            extra = f"[n={self.limit}]"
        return f"{self.type.value}{extra}"


@dataclass
class Plan:
    """An ordered pipeline of stages plus an estimated input size."""
    stages: List[Stage] = field(default_factory=list)
    input_rows: int = 1000

    def explain(self) -> str:
        """Render the plan like `scan -> filter[tag] -> aggregate`."""
        return " -> ".join(repr(s) for s in self.stages)


class QueryOptimizer:
    """
    Rule-based optimizer. Each rule is a pure function Plan -> Plan; optimize()
    applies them in a sensible order and returns a new Plan (does not mutate input).
    """

    def optimize(self, plan: Plan) -> Plan:
        """Apply all rewrite rules and return the optimized plan."""
        # TODO: copy the plan, then apply, in order:
        #   1. merge_filters
        #   2. push_tag_filters_into_scan
        #   3. reorder_filters_before_aggregate
        #   4. push_limit_down (only when safe)
        # Return the resulting Plan.
        raise NotImplementedError

    @staticmethod
    def merge_filters(plan: Plan) -> Plan:
        """
        Collapse consecutive FILTER stages into one whose selectivity is the product
        of the merged selectivities (independent-predicate assumption). Preserve
        on_tag only if ALL merged filters were tag filters.
        """
        # TODO: scan stages; when adjacent FILTERs appear, combine them.
        raise NotImplementedError

    @staticmethod
    def push_tag_filters_into_scan(plan: Plan) -> Plan:
        """
        Move FILTER stages with on_tag=True so they sit immediately after (or merge
        into) the SCAN — modeling predicate pushdown into the index. Keep field
        filters where they are (relative order otherwise preserved).
        """
        # TODO: pull out tag filters, re-insert them right after the SCAN stage.
        raise NotImplementedError

    @staticmethod
    def reorder_filters_before_aggregate(plan: Plan) -> Plan:
        """
        Ensure every FILTER runs BEFORE any AGGREGATE (filtering fewer rows is always
        cheaper than aggregating then filtering). Move a FILTER that appears after an
        AGGREGATE to just before the first AGGREGATE.

        NOTE: this is only valid when the filter is on raw columns, which we assume
        here (post-aggregation HAVING-style filters are out of scope).
        """
        # TODO: if a FILTER sits after an AGGREGATE, relocate it before the aggregate.
        raise NotImplementedError

    @staticmethod
    def push_limit_down(plan: Plan) -> Plan:
        """
        Push a trailing LIMIT earlier ONLY when it is result-preserving: a LIMIT can
        move above stages that don't change row identity/order in a way that affects
        which first-N rows are returned. Safe to push past a FILTER? No — filtering
        after limiting changes the result. Safe to push past AGGREGATE/GROUP? No.
        So: only push a LIMIT up past a leading SCAN when there are NO FILTER/GROUP/
        AGGREGATE stages between them (i.e. a pure scan+limit). Otherwise leave it.
        """
        # TODO: implement the conservative rule above (this is mostly a no-op except
        #       for the pure scan -> limit case; the point is learning WHEN not to).
        raise NotImplementedError

    @staticmethod
    def estimate_cost(plan: Plan) -> float:
        """
        Rough cost model: sum of rows flowing INTO each stage. Rows shrink by a
        filter's selectivity; a LIMIT caps rows at its n; SCAN emits input_rows.
        Lower total = better plan. Used to prove optimization helped.
        """
        # TODO: walk stages, tracking current row count; accumulate the input rows to
        #       each stage; apply selectivity/limit to update the running count.
        raise NotImplementedError


def test_optimization():
    print("Testing Query Optimization...")
    opt = QueryOptimizer()

    # Test 1: merge consecutive filters (selectivity multiplies)
    p = Plan([
        Stage(StageType.SCAN),
        Stage(StageType.FILTER, on_tag=True, selectivity=0.5),
        Stage(StageType.FILTER, on_tag=True, selectivity=0.2),
    ])
    merged = QueryOptimizer.merge_filters(p)
    filters = [s for s in merged.stages if s.type == StageType.FILTER]
    assert len(filters) == 1
    assert abs(filters[0].selectivity - 0.1) < 1e-9
    assert filters[0].on_tag is True
    print("✓ Test 1 passed: merge_filters")

    # Test 2: merged on_tag is False if any filter was a field filter
    p = Plan([
        Stage(StageType.SCAN),
        Stage(StageType.FILTER, on_tag=True, selectivity=0.5),
        Stage(StageType.FILTER, on_tag=False, selectivity=0.5),
    ])
    merged = QueryOptimizer.merge_filters(p)
    f = [s for s in merged.stages if s.type == StageType.FILTER][0]
    assert f.on_tag is False
    print("✓ Test 2 passed: mixed merge is field filter")

    # Test 3: tag filter pushed to just after scan
    p = Plan([
        Stage(StageType.SCAN),
        Stage(StageType.AGGREGATE),
        Stage(StageType.FILTER, on_tag=True, selectivity=0.3),
    ])
    pushed = QueryOptimizer.push_tag_filters_into_scan(p)
    assert pushed.stages[0].type == StageType.SCAN
    assert pushed.stages[1].type == StageType.FILTER and pushed.stages[1].on_tag
    print("✓ Test 3 passed: push_tag_filters_into_scan")

    # Test 4: filter after aggregate moves before it
    p = Plan([
        Stage(StageType.SCAN),
        Stage(StageType.AGGREGATE),
        Stage(StageType.FILTER, on_tag=False, selectivity=0.4),
    ])
    r = QueryOptimizer.reorder_filters_before_aggregate(p)
    agg_idx = [i for i, s in enumerate(r.stages) if s.type == StageType.AGGREGATE][0]
    filt_idx = [i for i, s in enumerate(r.stages) if s.type == StageType.FILTER][0]
    assert filt_idx < agg_idx
    print("✓ Test 4 passed: filters reordered before aggregate")

    # Test 5: limit NOT pushed past a filter (would change results)
    p = Plan([
        Stage(StageType.SCAN),
        Stage(StageType.FILTER, on_tag=False, selectivity=0.5),
        Stage(StageType.LIMIT, limit=10),
    ])
    r = QueryOptimizer.push_limit_down(p)
    assert r.stages[-1].type == StageType.LIMIT, "limit must stay after the filter"
    print("✓ Test 5 passed: limit not pushed past filter")

    # Test 6: limit pushed up in a pure scan+limit
    p = Plan([Stage(StageType.SCAN), Stage(StageType.LIMIT, limit=10)])
    r = QueryOptimizer.push_limit_down(p)
    assert r.stages[0].type == StageType.LIMIT and r.stages[1].type == StageType.SCAN
    print("✓ Test 6 passed: limit pushed into pure scan")

    # Test 7: full optimize lowers estimated cost
    p = Plan([
        Stage(StageType.SCAN),
        Stage(StageType.AGGREGATE),
        Stage(StageType.FILTER, on_tag=True, selectivity=0.1),
        Stage(StageType.FILTER, on_tag=True, selectivity=0.5),
    ], input_rows=10000)
    before = QueryOptimizer.estimate_cost(p)
    optimized = opt.optimize(p)
    after = QueryOptimizer.estimate_cost(optimized)
    assert after < before, f"optimize should reduce cost: {before} -> {after}"
    # filters should now precede the aggregate and be merged
    types = [s.type for s in optimized.stages]
    assert types.index(StageType.FILTER) < types.index(StageType.AGGREGATE)
    print(f"✓ Test 7 passed: optimize cost {before:.0f} -> {after:.0f}")
    print(f"   plan: {optimized.explain()}")

    # Test 8: optimize does not mutate the input plan
    original_len = len(p.stages)
    opt.optimize(p)
    assert len(p.stages) == original_len
    print("✓ Test 8 passed: optimize is non-destructive")

    print("\n🎉 All query optimization tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement the rewrite rules, estimate_cost, and optimize.
    2. Run: python day20_optimization.py
    3. All 8 tests should pass.

    Success criteria:
    - Rules are pure (return new plans, never mutate the input)
    - Filters merge, push toward the scan, and precede aggregation
    - LIMIT is only pushed when it cannot change the result
    - optimize() measurably lowers the estimated cost

    Next steps:
    - Day 21: advanced aggregations (rate/derivative) — the last query building block.
    - Think about: which of these rewrites could ever change the ANSWER, and why the
      LIMIT rule is deliberately conservative.
    """
    test_optimization()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Logical Plan
   - Representing a query as an inspectable list of stages (not imperative code) is
     what makes optimization possible — the same "data not code" lesson as Day 15's
     predicate tree, one level up.

2. Rule-Based (Heuristic) Optimization
   - Apply always-good rewrites: merge adjacent filters, push selective/index-able
     work down, do reductions late. Cheap, predictable, and covers most of the win
     before you ever need a cost model.

3. Cost Estimation & Selectivity
   - Selectivity (surviving fraction) predicts how rows shrink through the pipeline.
     Summing rows-into-each-stage gives a comparable cost so you can PROVE a rewrite
     helped rather than assume it.

4. Correctness of Reordering
   - Not every reorder is legal. Filtering before aggregating is always fine; limiting
     before filtering is NOT (you'd cap the wrong rows). A good optimizer is defined as
     much by the rewrites it REFUSES as the ones it applies.

Connection to InfluxDB:
- The storage engine pushes predicates and time bounds into the read path (like
  push_tag_filters_into_scan); Flux's planner fuses and reorders transformations. Both
  are rule-based rewrites over a plan, exactly like this.

Trade-offs:
- Heuristic rules are fast but can miss context-dependent wins that a cost-based
  optimizer (join/scan ordering by real statistics) would find. For a single-table
  time-series engine, heuristics capture nearly all the benefit.
"""
