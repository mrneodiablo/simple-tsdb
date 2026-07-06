#!/usr/bin/env python3
"""
Week 3 Integration Lab: Query Processing
========================================

This lab wires together every Week 3 building block into one query engine and runs
the kind of queries a monitoring dashboard actually issues: filter -> window ->
group -> aggregate, plus percentiles and counter rates.

Scenario: HTTP Service Dashboard
You have a day of HTTP request metrics across services and regions. You answer:
  - "p95 latency where status=error"                        (filter + percentile)
  - "mean latency per 5-minute window"                      (time windows)
  - "request count per (service, region)"                   (group by)
  - "requests/sec from the total counter, across a restart" (rate + reset handling)
  - and prove the optimizer lowers a query's estimated cost.

Success Criteria:
- Filtering matches a brute-force ground truth
- Windowed means align to clean 5m boundaries
- Group-by counts reconcile with the total
- Percentiles agree with an exact reference
- Counter rate stays non-negative across a reset
- The optimizer reduces estimated query cost
"""

import os
import sys
import time
import random
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "exercises", "week3_querying"))

try:
    from day15_basic_filtering import FilterEngine, AND, tag, fld, Op
    from day16_aggregations import Mean, Count, aggregate_field
    from day17_percentiles import exact_percentile, HistogramQuantile
    from day18_time_windows import WindowAggregator, parse_duration, window_start
    from day19_groupby import GroupByEngine
    from day20_optimization import (
        QueryOptimizer, Plan, Stage, StageType,
    )
    from day21_advanced_agg import Sample, rate, rate_over_window
except ImportError as e:
    print(f"⚠️  Import Error: {e}")
    print("Complete Week 3 exercises (day15-day21) before running this lab.")
    sys.exit(1)


SERVICES = ["auth", "catalog", "checkout", "search"]
REGIONS = ["us-west-2", "us-east-1", "eu-central-1"]
STATUSES = ["ok", "ok", "ok", "ok", "error"]  # ~20% errors


def generate_dataset(num_points: int = 20000, span_seconds: int = 86400) -> List[Dict[str, Any]]:
    """Generate HTTP request points spread across `span_seconds` (one day)."""
    print(f"🔄 Generating {num_points:,} HTTP request points over {span_seconds/3600:.0f}h...")
    base = 1_700_000_000  # fixed epoch base for stable window alignment
    points = []
    for _ in range(num_points):
        ts = base + random.uniform(0, span_seconds)
        status = random.choice(STATUSES)
        # errors tend to be slower -> a fatter tail
        latency = random.gauss(80, 20) if status == "ok" else random.gauss(300, 120)
        latency = max(1.0, latency)
        points.append({
            "measurement": "http_requests",
            "timestamp": ts,
            "tags": {
                "service": random.choice(SERVICES),
                "region": random.choice(REGIONS),
                "status": status,
            },
            "fields": {"latency_ms": round(latency, 2)},
        })
    points.sort(key=lambda p: p["timestamp"])
    print(f"✅ Generated {num_points:,} points")
    return points, base


def run_integration_test():
    print("=" * 60)
    print("🧪 Week 3 Integration Lab: Query Processing")
    print("=" * 60)

    points, base = generate_dataset(20000)

    # ------------------------------------------------------------------
    # Test 1: Filter — errors only
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 1: Filtering (status = error)")
    print("=" * 40)

    engine = FilterEngine()
    errors = engine.apply(points, tag("status", Op.EQ, "error"))
    expected = [p for p in points if p["tags"]["status"] == "error"]
    assert len(errors) == len(expected), "filter mismatch vs brute force"
    print(f"✅ Filtered to {len(errors):,} error points (of {len(points):,})")

    # compound filter: slow errors in us-west-2
    pred = AND(
        tag("status", Op.EQ, "error"),
        tag("region", Op.EQ, "us-west-2"),
        fld("latency_ms", Op.GT, 200.0),
    )
    slow = engine.apply(points, pred)
    gt = [p for p in points if p["tags"]["status"] == "error"
          and p["tags"]["region"] == "us-west-2" and p["fields"]["latency_ms"] > 200.0]
    assert len(slow) == len(gt)
    print(f"✅ Compound filter (slow us-west errors): {len(slow):,} points")

    # ------------------------------------------------------------------
    # Test 2: Percentiles on error latency
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 2: Percentiles (error latency p50/p95/p99)")
    print("=" * 40)

    lat = [p["fields"]["latency_ms"] for p in errors]
    p50 = exact_percentile(lat, 50)
    p95 = exact_percentile(lat, 95)
    p99 = exact_percentile(lat, 99)
    assert p50 <= p95 <= p99, "percentiles must be monotonic"

    hist = HistogramQuantile(lo=0, hi=1000, num_buckets=200)
    hist.add_all(lat)
    approx_p95 = hist.percentile(95)
    err = abs(approx_p95 - p95)
    print(f"✅ exact p50={p50:.1f}  p95={p95:.1f}  p99={p99:.1f} ms")
    print(f"   histogram p95={approx_p95:.1f} ms (error {err:.1f} ms, bounded memory)")
    assert err <= 10, "approximate p95 should be within a bucket width"

    # ------------------------------------------------------------------
    # Test 3: Time windows — mean latency per 5m
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 3: Time Windows (mean latency per 5m)")
    print("=" * 40)

    interval = parse_duration("5m")
    wa = WindowAggregator(agg_factory=Mean, field_key="latency_ms")
    windows = wa.aggregate(points, interval=interval, origin=base)
    # boundaries must be aligned to base + k*interval
    assert all((w.start - base) % interval == 0 for w in windows), "windows not aligned"
    total_windowed = sum(w.count for w in windows)
    assert total_windowed == len(points), "every point must land in a window"
    print(f"✅ {len(windows)} windows of 5m; all points bucketed; boundaries aligned")
    print(f"   first window mean latency: {windows[0].value:.1f} ms ({windows[0].count} pts)")

    # ------------------------------------------------------------------
    # Test 4: Group by (service, region) — request counts
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 4: Group By (count per service+region)")
    print("=" * 40)

    gb = GroupByEngine(agg_factory=Count, field_key="latency_ms")
    groups = gb.group(points, ["service", "region"])
    assert sum(g.count for g in groups) == len(points), "group counts must reconcile"
    assert len(groups) <= len(SERVICES) * len(REGIONS)
    top = max(groups, key=lambda g: g.count)
    print(f"✅ {len(groups)} (service,region) groups; counts reconcile to {len(points):,}")
    print(f"   busiest group {top.key}: {top.count:,} requests")

    # ------------------------------------------------------------------
    # Test 5: Counter rate across a reset
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 5: Counter Rate with Reset Handling")
    print("=" * 40)

    # Build a per-second counter that restarts halfway (simulate a deploy).
    counter_samples = []
    val = 0
    for i in range(60):
        if i == 30:   # reset
            val = 0
        val += random.randint(5, 15)
        counter_samples.append(Sample(timestamp=i, value=val))
    rates = rate(counter_samples, counter=True)
    assert all(r.value >= 0 for r in rates), "counter rate must never go negative"
    avg = rate_over_window(counter_samples, counter=True)
    print(f"✅ {len(rates)} per-interval rates, all non-negative across the reset")
    print(f"   average rate over window: {avg:.2f} /s")

    # ------------------------------------------------------------------
    # Test 6: Optimizer lowers estimated cost
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 6: Query Optimization")
    print("=" * 40)

    plan = Plan([
        Stage(StageType.SCAN),
        Stage(StageType.AGGREGATE),
        Stage(StageType.FILTER, on_tag=True, selectivity=0.2),
        Stage(StageType.FILTER, on_tag=True, selectivity=0.5),
    ], input_rows=len(points))
    opt = QueryOptimizer()
    before = QueryOptimizer.estimate_cost(plan)
    optimized = opt.optimize(plan)
    after = QueryOptimizer.estimate_cost(optimized)
    assert after < before
    print(f"✅ Optimized plan: {optimized.explain()}")
    print(f"   estimated cost {before:.0f} -> {after:.0f} ({before/after:.1f}x cheaper)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Summary")
    print("=" * 40)
    print(f"   Points queried:        {len(points):,}")
    print(f"   Error p95 latency:     {p95:.1f} ms")
    print(f"   5m windows produced:   {len(windows)}")
    print(f"   (service,region) grps: {len(groups)}")
    print(f"   Optimizer speedup:     {before/after:.1f}x (estimated)")

    print("\n🎉 Week 3 Integration Lab Completed Successfully!")
    print("🚀 Ready to proceed to Week 4: API Layer")

    return {"points": len(points), "p95": p95, "windows": len(windows), "groups": len(groups)}


if __name__ == "__main__":
    """
    Run this lab after completing Week 3 exercises (day15-day21).

    This lab will:
    1. Generate 20,000 realistic HTTP request points over one day
    2. Filter, then compute exact + approximate percentiles on error latency
    3. Aggregate mean latency into aligned 5-minute windows
    4. Group request counts by (service, region) and reconcile totals
    5. Compute a counter rate across a simulated restart (reset handling)
    6. Prove the optimizer lowers a query's estimated cost

    Expected results:
    - Every query reconciles with a brute-force / exact reference
    - Percentiles are monotonic and the histogram is within a bucket width
    - Counter rates never go negative across the reset
    - The optimized plan is cheaper than the naive one
    """
    random.seed(42)
    try:
        results = run_integration_test()
        print("\n✅ Lab completed successfully!")
        print("   Continue to Week 4: API Layer")
    except Exception as e:
        print(f"\n❌ Lab failed with error: {e}")
        print("   Review your Week 3 implementations and try again")
        raise
