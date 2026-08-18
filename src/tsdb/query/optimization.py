#!/usr/bin/env python3

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
        new_plan = Plan(stages=list(plan.stages), input_rows=plan.input_rows)
        new_plan = self.merge_filters(new_plan)
        new_plan = self.push_tag_filters_into_scan(new_plan)
        new_plan = self.reorder_filters_before_aggregate(new_plan)
        new_plan = self.push_limit_down(new_plan)
        return new_plan


    @staticmethod
    def merge_filters(plan: Plan) -> Plan:
        """
        Collapse consecutive FILTER stages into one whose selectivity is the product
        of the merged selectivities (independent-predicate assumption). Preserve
        on_tag only if ALL merged filters were tag filters.
        """
        # TODO: scan stages; when adjacent FILTERs appear, combine them.
        new_stages = []
        i = 0
        while i < len(plan.stages):
            stage = plan.stages[i]
            if stage.type == StageType.FILTER:
                # Start merging consecutive filters
                merged_selectivity = stage.selectivity
                merged_on_tag = stage.on_tag
                j = i + 1
                while j < len(plan.stages) and plan.stages[j].type == StageType.FILTER:
                    merged_selectivity *= plan.stages[j].selectivity
                    merged_on_tag = merged_on_tag and plan.stages[j].on_tag
                    j += 1
                new_stages.append(Stage(StageType.FILTER, on_tag=merged_on_tag, selectivity=merged_selectivity))
                i = j  # Skip the merged filters
            else:
                new_stages.append(stage)
                i += 1
        return Plan(stages=new_stages, input_rows=plan.input_rows)

    @staticmethod
    def push_tag_filters_into_scan(plan: Plan) -> Plan:
        """
        Move FILTER stages with on_tag=True so they sit immediately after (or merge
        into) the SCAN — modeling predicate pushdown into the index. Keep field
        filters where they are (relative order otherwise preserved).
        """
        # TODO: pull out tag filters, re-insert them right after the SCAN stage.
        new_stages = []
        tag_filters = []
        for stage in plan.stages:
            if stage.type == StageType.FILTER and stage.on_tag:
                tag_filters.append(stage)
            else:
                new_stages.append(stage)
        # Find the index of the first SCAN stage
        scan_index = next((i for i, s in enumerate(new_stages) if s.type == StageType.SCAN), None)
        if scan_index is not None:
            # Insert tag filters right after the SCAN stage
            new_stages = new_stages[:scan_index + 1] + tag_filters + new_stages[scan_index + 1:]
        else:
            # If no SCAN stage, just append tag filters at the end
            new_stages.extend(tag_filters)
        return Plan(stages=new_stages, input_rows=plan.input_rows)

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
        new_stages = []
        aggregate_index = next((i for i, s in enumerate(plan.stages) if s.type == StageType.AGGREGATE), None)
        if aggregate_index is not None:
            filters_before_aggregate = [s for s in plan.stages[:aggregate_index] if s.type == StageType.FILTER]
            filters_after_aggregate = [s for s in plan.stages[aggregate_index + 1:] if s.type == StageType.FILTER]
            non_filter_before = [s for s in plan.stages[:aggregate_index] if s.type != StageType.FILTER]
            non_filter_after = [s for s in plan.stages[aggregate_index + 1:] if s.type != StageType.FILTER]
            new_stages = (
                non_filter_before +
                filters_before_aggregate +
                filters_after_aggregate +
                [plan.stages[aggregate_index]] +
                non_filter_after
            )
        else:
            new_stages = plan.stages
        return Plan(stages=new_stages, input_rows=plan.input_rows)

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
        new_stages = list(plan.stages)
        limit_index = next((i for i, s in enumerate(new_stages) if s.type == StageType.LIMIT), None)
        if limit_index is not None:
            # Check if there are only SCAN stages before the LIMIT
            if all(s.type == StageType.SCAN for s in new_stages[:limit_index]):
                # Move the LIMIT to the front
                limit_stage = new_stages.pop(limit_index)
                new_stages.insert(0, limit_stage)
        return Plan(stages=new_stages, input_rows=plan.input_rows)

    @staticmethod
    def estimate_cost(plan: Plan) -> float:
        """
        Rough cost model: sum of rows flowing INTO each stage. Rows shrink by a
        filter's selectivity; a LIMIT caps rows at its n; SCAN emits input_rows.
        Lower total = better plan. Used to prove optimization helped.
        """
        # TODO: walk stages, tracking current row count; accumulate the input rows to
        #       each stage; apply selectivity/limit to update the running count.
        total_cost = 0
        current_rows = plan.input_rows
        for stage in plan.stages:
            total_cost += current_rows
            if stage.type == StageType.FILTER:
                current_rows *= stage.selectivity
            elif stage.type == StageType.LIMIT and stage.limit is not None:
                current_rows = min(current_rows, stage.limit)
            # SCAN, AGGREGATE, GROUP do not change row count in this model
        return total_cost

