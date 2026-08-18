"""
Query Layer for Time-Series Database
====================================

Filtering, aggregation, windowing, grouping, and query optimization over the points
that the storage + index layers locate. Re-exports each module's public API so callers
can do e.g. `from tsdb.query import FilterEngine, WindowAggregator`.
"""

from .basic_filtering import (
    FilterEngine, Comparison, BoolNode, Op, BoolKind, tag, fld, AND, OR,
)
from .aggregations import (
    Aggregator, Count, Sum, Mean, Min, Max, aggregate_field, AGGREGATORS, is_number,
)
from .percentiles import exact_percentile, HistogramQuantile
from .time_windows import WindowAggregator, WindowResult, parse_duration, window_start
from .groupby import GroupByEngine, Group, make_group_key
from .optimization import QueryOptimizer, Plan, Stage, StageType
from .advanced_agg import (
    Sample, derivative, rate, total_increase, rate_over_window, samples_from_points,
)

__all__ = [
    # basic_filtering
    "FilterEngine", "Comparison", "BoolNode", "Op", "BoolKind",
    "tag", "fld", "AND", "OR",
    # aggregations
    "Aggregator", "Count", "Sum", "Mean", "Min", "Max",
    "aggregate_field", "AGGREGATORS", "is_number",
    # percentiles
    "exact_percentile", "HistogramQuantile",
    # time_windows
    "WindowAggregator", "WindowResult", "parse_duration", "window_start",
    # groupby
    "GroupByEngine", "Group", "make_group_key",
    # optimization
    "QueryOptimizer", "Plan", "Stage", "StageType",
    # advanced_agg
    "Sample", "derivative", "rate", "total_increase",
    "rate_over_window", "samples_from_points",
]
