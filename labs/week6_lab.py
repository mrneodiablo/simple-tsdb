#!/usr/bin/env python3
"""
Week 6 Final Lab: Capstone Demonstration
========================================

The finale. This lab exercises the whole Week 6 toolkit on a realistic version of the
Week 1-5 system and produces the capstone artifact — a Markdown report:

    1. PROFILE the system (real timings) and rank bottlenecks + Amdahl prediction (Day 33)
    2. OPTIMIZE the top bottleneck (indexed lookup vs full scan) with a correctness
       guard and a measured speedup (Day 34)
    3. APPLY the learnings to a real work system as prioritized recommendations (Day 35)
    4. DOCUMENT everything as a shareable Markdown report, written to docs/ (Day 36)

Success Criteria:
- Profiling ranks the hotspots and predicts an optimization ceiling
- The optimization is proven BOTH correct and faster (improved == True)
- The application plan surfaces at least one quick win
- A structured Markdown report is generated (and saved to docs/capstone_report.md)
"""

import os
import sys
import time
import random
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "exercises", "week6_production"))

try:
    from day33_bottleneck_analysis import BottleneckAnalyzer
    from day34_optimization import Optimizer
    from day35_work_application import ApplicationPlan, Recommendation
    from day36_documentation import ReportBuilder
except ImportError as e:
    print(f"⚠️  Import Error: {e}")
    print("Complete Week 6 exercises (day33-day36) before running this lab.")
    sys.exit(1)


TIMER = time  # time.perf_counter() satisfies the Timer protocol


def build_dataset(n: int = 20000):
    rng = random.Random(2024)
    hosts = [f"web-{i:02d}" for i in range(20)]
    store: List[Dict[str, Any]] = []
    tag_index: Dict[tuple, List[Dict[str, Any]]] = {}
    for i in range(n):
        host = rng.choice(hosts)
        p = {"measurement": "cpu", "timestamp": float(i),
             "tags": {"host": host}, "fields": {"value": rng.uniform(0, 100)}}
        store.append(p)
        tag_index.setdefault(("host", host), []).append(p)
    return store, tag_index


def run_capstone():
    print("=" * 60)
    print("🎓 Week 6 Final Lab: Capstone Demonstration")
    print("=" * 60)

    store, tag_index = build_dataset(20000)

    def scan_query(host):
        return [p for p in store if p["tags"]["host"] == host]

    def indexed_query(host):
        return tag_index.get(("host", host), [])

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nStep 1: Profile & rank bottlenecks\n" + "=" * 40)

    def timeit(fn, repeats):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        return time.perf_counter() - t0

    timings = {
        "write_ingest": timeit(lambda: build_dataset(2000), 1),
        "scan_query": timeit(lambda: scan_query("web-01"), 50),
        "indexed_query": timeit(lambda: indexed_query("web-01"), 50),
    }
    analyzer = BottleneckAnalyzer(timings)
    ranked = analyzer.rank()
    print("   Hotspot ranking:")
    for h in ranked:
        print(f"     {h.operation:<16} {h.total_time*1e3:>8.2f} ms  "
              f"{h.share*100:>5.1f}%  (cum {h.cumulative_share*100:>5.1f}%)")
    top = ranked[0]
    ceiling = analyzer.max_speedup(top.share)
    print(f"   Top bottleneck: {top.operation} ({top.share*100:.1f}% of time)")
    print(f"   Amdahl ceiling if it vanished: {ceiling:.2f}x overall")
    assert len(ranked) == 3

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nStep 2: Optimize (indexed vs scan) with proof\n" + "=" * 40)
    opt = Optimizer(TIMER)
    result = opt.optimize("host lookup", baseline_fn=scan_query,
                          optimized_fn=indexed_query, inputs=["web-01", "web-05"],
                          iterations=20)
    print(f"   correct:   {result.correct}")
    print(f"   baseline:  {result.baseline_time*1e3:.2f} ms")
    print(f"   optimized: {result.optimized_time*1e3:.3f} ms")
    print(f"   speedup:   {result.speedup:.0f}x  -> improved={result.improved}")
    assert result.correct is True, "optimized lookup must return identical results"
    assert result.improved is True, "indexed lookup must be faster than the scan"

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nStep 3: Apply to a real work system\n" + "=" * 40)
    plan = ApplicationPlan()
    plan.add(Recommendation(
        "Slow InfluxDB point queries", "an inverted tag index turns scans into lookups",
        "ensure selective tags are indexed / avoid full-measurement scans", 5, 2))
    plan.add(Recommendation(
        "Write throughput", "batching amortizes per-write overhead",
        "raise client batch size (see Week 5 amortization curve)", 5, 1))
    plan.add(Recommendation(
        "Index memory growth", "cardinality drives index size",
        "cap high-cardinality tags; monitor series count", 4, 3))
    plan.add(Recommendation(
        "Storage cost", "columnar + delta/RLE compression saves space",
        "verify compression settings", 2, 4))
    for r in plan.prioritized():
        print(f"     [{r.priority:.1f}] {r.challenge} -> {r.action}")
    quick = plan.quick_wins()
    print(f"   Quick wins: {[r.challenge for r in quick]}")
    assert len(quick) >= 1

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nStep 4: Generate the capstone report\n" + "=" * 40)
    report = (
        ReportBuilder("simple-timeseries-db — 6-Week Capstone Report")
        .section("Overview",
                 "Built a time-series database from scratch over six weeks:",
                 "storage, indexing, query engine, API layer, benchmarking, and analysis.")
        .metric_table("Key Results", {
            "dataset points": len(store),
            "top bottleneck": f"{top.operation} ({top.share*100:.0f}%)",
            "optimization speedup": f"{result.speedup:.0f}x",
            "optimization correct": result.correct,
        })
        .bullets("Quick Wins for Production", [f"{r.challenge}: {r.action}" for r in quick])
        .section("Conclusion",
                 "Indexing selective lookups and batching writes deliver the biggest,",
                 "cheapest wins — verified by profiling and a correctness-guarded benchmark.")
        .build()
    )

    # structural assertions
    assert report.startswith("# simple-timeseries-db")
    for h in ["## Overview", "## Key Results", "## Quick Wins for Production", "## Conclusion"]:
        assert h in report, f"missing section {h}"
    assert f"{result.speedup:.0f}x" in report

    # save the artifact (file I/O is fine in the lab)
    out_path = os.path.join(os.path.dirname(__file__), "..", "docs", "capstone_report.md")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"   ✅ Report written to docs/capstone_report.md ({len(report)} chars)")
    except OSError as e:
        print(f"   ⚠️  Could not write report file: {e}")

    print("\n--- report preview ---")
    print("\n".join(report.splitlines()[:12]))
    print("...")

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nSummary\n" + "=" * 40)
    print(f"   Top bottleneck:     {top.operation} ({top.share*100:.0f}%)")
    print(f"   Optimization:       {result.speedup:.0f}x, correct={result.correct}")
    print(f"   Quick wins:         {len(quick)}")
    print("\n🎉🎓 Week 6 Capstone Completed — the 6-week journey is done!")
    print("🚀 You built, benchmarked, optimized, and documented a time-series database.")
    return {"speedup": result.speedup, "quick_wins": len(quick)}


if __name__ == "__main__":
    """
    Run this lab after completing Week 6 exercises (day33-day36).

    This lab will:
    1. Profile the system and rank bottlenecks (Amdahl ceiling for the top one)
    2. Optimize the hot path (indexed vs scan) with a correctness guard + speedup
    3. Prioritize real-world recommendations and surface quick wins
    4. Generate + save the capstone Markdown report

    Expected results:
    - A hotspot ranking dominated by the full scan
    - improved == True (indexed lookup is correct AND faster)
    - At least one quick win
    - A well-structured report at docs/capstone_report.md
    """
    try:
        run_capstone()
        print("\n✅ Capstone lab completed successfully!")
    except Exception as e:
        print(f"\n❌ Lab failed with error: {e}")
        print("   Review your Week 6 implementations and try again")
        raise
