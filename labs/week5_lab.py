#!/usr/bin/env python3
"""
Week 5 Integration Lab: Comparison & Analysis
=============================================

This lab runs the full Week 5 toolkit against a realistic in-memory version of the
Week 1-4 system, using REAL wall-clock timing (the one place that's appropriate), and
produces a comparison report:

    - Write throughput vs batch size (Day 30 harness over an in-memory store)
    - Query latency: indexed tag lookup vs brute-force full scan (Day 31)
    - Architecture recommendation for two workloads (Day 32)

Scenario: measure this project honestly
Generate a monitoring dataset, build a store + a tiny tag index, and benchmark the
write and read paths. Then step back and let the architecture analyzer recommend when
this design is the right tool vs when InfluxDB is.

Success Criteria:
- The write sweep completes and reports positive throughput for every batch size
- The indexed tag lookup is faster than the full scan (speedup > 1)
- The recommender picks InfluxDB for write-heavy ingestion and this project for
  learning/debuggability
- A structured report is produced
"""

import os
import sys
import time
import random
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "exercises", "week5_comparison"))

try:
    from day29_benchmark_setup import Benchmark
    from day30_write_benchmark import WriteBenchmark, WorkloadGenerator
    from day31_query_benchmark import QueryBenchmark
    from day32_architecture_analysis import (
        ArchitectureComparison, INFLUXDB, SIMPLE_TSDB, WRITE_HEAVY, LEARNING_DEBUGGABILITY,
    )
except ImportError as e:
    print(f"⚠️  Import Error: {e}")
    print("Complete Week 5 exercises (day29-day32) before running this lab.")
    sys.exit(1)


# `time` satisfies the Timer protocol: time.perf_counter() -> float.
TIMER = time


def build_dataset(n: int = 20000):
    """Return (store, tag_index) where store is a list of points and tag_index maps
    (tag_key, tag_value) -> list of points (mirrors Week 2's inverted index)."""
    rng = random.Random(123)
    hosts = [f"web-{i:02d}" for i in range(20)]
    store: List[Dict[str, Any]] = []
    tag_index: Dict[tuple, List[Dict[str, Any]]] = {}
    for i in range(n):
        host = rng.choice(hosts)
        region = rng.choice(["us-west", "us-east", "eu"])
        p = {"measurement": "cpu", "timestamp": float(i),
             "tags": {"host": host, "region": region},
             "fields": {"value": rng.uniform(0, 100)}}
        store.append(p)
        for kv in (("host", host), ("region", region)):
            tag_index.setdefault(kv, []).append(p)
    return store, tag_index


def run_integration_test():
    print("=" * 60)
    print("🧪 Week 5 Integration Lab: Comparison & Analysis")
    print("=" * 60)

    report: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nTest 1: Write throughput vs batch size\n" + "=" * 40)
    written: List[Dict[str, Any]] = []

    def write_fn(batch):
        # simulate a little fixed per-batch overhead (index bookkeeping intent)
        _ = len(repr(batch[0])) if batch else 0
        written.extend(batch)

    wb = WriteBenchmark(TIMER, write_fn, WorkloadGenerator(seed=7))
    results = wb.sweep(batch_sizes=[1, 50, 500], total_points=5000)
    for r in results:
        assert r.throughput > 0
        print(f"   batch={r.batch_size:>4}: {r.throughput:>12,.0f} pts/s "
              f"(mean batch {r.mean_batch_latency*1e6:.1f} µs)")
    report["write_throughput"] = {r.batch_size: r.throughput for r in results}
    print("✅ Write sweep completed; throughput positive for all batch sizes")

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nTest 2: Query — indexed vs full scan\n" + "=" * 40)
    store, tag_index = build_dataset(20000)

    def scan_lookup():
        return [p for p in store if p["tags"]["host"] == "web-01"]

    def indexed_lookup():
        return tag_index.get(("host", "web-01"), [])

    # sanity: both find the same points
    assert len(indexed_lookup()) == len(scan_lookup()) > 0

    qb = QueryBenchmark(TIMER)
    cmp = qb.compare("point_lookup", indexed_lookup, scan_lookup, iterations=20)
    print(f"   indexed mean: {cmp.indexed_mean*1e6:>10.2f} µs")
    print(f"   scan    mean: {cmp.scan_mean*1e6:>10.2f} µs")
    print(f"   speedup:      {cmp.speedup:>10.1f}x")
    assert cmp.indexed_wins, "indexed lookup should beat a full scan"
    assert cmp.speedup > 1.0
    report["query_speedup"] = cmp.speedup

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nTest 3: Benchmark harness sanity\n" + "=" * 40)
    bench = Benchmark(TIMER)
    res = bench.run("noop", fn=lambda: sum(range(100)), iterations=50, warmup=5)
    assert res.iterations == 50 and res.mean >= 0 and res.p95 >= res.median
    print(f"✅ harness: mean={res.mean*1e9:.0f} ns, p95={res.p95*1e9:.0f} ns, "
          f"{res.ops_per_sec:,.0f} ops/s")

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nTest 4: Architecture recommendation\n" + "=" * 40)
    arch = ArchitectureComparison()
    arch.register(INFLUXDB)
    arch.register(SIMPLE_TSDB)

    rec_write = arch.recommend(WRITE_HEAVY)
    rec_learn = arch.recommend(LEARNING_DEBUGGABILITY)
    print(f"   write-heavy ingestion   -> {rec_write.name}")
    print(f"   learning/debuggability  -> {rec_learn.name}")
    assert rec_write.name == INFLUXDB.name
    assert rec_learn.name == SIMPLE_TSDB.name
    report["recommendations"] = {
        "write_heavy": rec_write.name, "learning": rec_learn.name,
    }

    print("\n   Trade-off matrix:")
    matrix = arch.matrix()
    dims = list(next(iter(matrix.values())).keys())
    print("   " + "architecture".ljust(38) + "  ".join(d[:6] for d in dims))
    for name, scores in matrix.items():
        print("   " + name.ljust(38) + "  ".join(f"{scores[d]:>6}" for d in dims))
    print("✅ Recommendations match expectations")

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nSummary\n" + "=" * 40)
    best_tps = max(report["write_throughput"].values())
    print(f"   Peak write throughput:  {best_tps:,.0f} pts/s")
    print(f"   Index vs scan speedup:  {report['query_speedup']:.1f}x")
    print(f"   Write-heavy pick:       {report['recommendations']['write_heavy']}")
    print(f"   Learning pick:          {report['recommendations']['learning']}")

    print("\n🎉 Week 5 Integration Lab Completed Successfully!")
    print("🚀 Ready to proceed to Week 6: Production Application")
    return report


if __name__ == "__main__":
    """
    Run this lab after completing Week 5 exercises (day29-day32).

    This lab will:
    1. Benchmark write throughput across batch sizes (real timing)
    2. Compare an indexed tag lookup against a full scan and report the speedup
    3. Sanity-check the benchmark harness statistics
    4. Recommend an architecture per workload and print the trade-off matrix

    Expected results:
    - Positive write throughput for every batch size
    - Indexed lookup faster than the full scan (speedup > 1)
    - InfluxDB recommended for write-heavy, this project for learning/debuggability
    """
    try:
        run_integration_test()
        print("\n✅ Lab completed successfully!")
        print("   Continue to Week 6: Production Application")
    except Exception as e:
        print(f"\n❌ Lab failed with error: {e}")
        print("   Review your Week 5 implementations and try again")
        raise
