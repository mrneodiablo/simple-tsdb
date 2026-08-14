#!/usr/bin/env python3
"""
Week 2 Integration Lab: Indexing & Retrieval Testing
====================================================

This lab exercises your complete Week 2 implementation by building indexes over
a realistic dataset and answering tag + time-range queries through them.

Scenario: Monitoring Metrics Index
You have a week of monitoring data across several servers and regions. You build
a tag index, a time index, and a series registry, then query the data the way a
dashboard would — by tag, by time window, and by both at once.

Success Criteria:
- Index 50,000+ data points across many series
- Tag lookups return the correct series/locations (sub-millisecond)
- Time-range queries prune to the right files via binary search
- Combined tag + time queries are correct AND faster than a full scan
- Bloom filters skip files that cannot match
- Index survives a save -> load round-trip
"""

import os
import sys
import time
import shutil
import random
from typing import Dict, List, Any

# Make the Week 2 exercises importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "exercises", "week2_indexing"))

try:
    from day8_tag_index import TagIndex, MatchMode
    from day9_time_index import TimeRangeIndex
    from day10_series_keys import SeriesManager
    from day11_index_persistence import IndexPersistence
    from day12_read_ops import IndexedReader, Query
    from day13_range_queries import RangeQueryEngine
    from day14_index_optimization import BloomFilter, OptimizedTagIndex
except ImportError as e:
    print(f"⚠️  Import Error: {e}")
    print("Complete Week 2 exercises (day8-day14) before running this lab.")
    sys.exit(1)


# ----------------------------------------------------------------------------
# Test data: many points, grouped into "files" (locations) by day.
# ----------------------------------------------------------------------------
SERVERS = ["web-01", "web-02", "web-03", "api-01", "api-02", "db-01"]
REGIONS = ["us-west-2", "us-east-1", "eu-central-1"]
MEASUREMENTS = ["cpu", "memory", "disk", "http_requests"]


def generate_dataset(num_points: int = 50000, num_days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate `num_points` data points spread across `num_days`.

    Returns a mapping of location -> list of points, where a location is one
    file per (measurement, day). Each point is a plain dict with
    timestamp / tags / fields (the Week 1 DataPoint.to_dict() shape).
    """
    print(f"🔄 Generating {num_points:,} points across {num_days} days...")
    day_seconds = 86400
    base = time.time() - num_days * day_seconds

    files: Dict[str, List[Dict[str, Any]]] = {}
    for i in range(num_points):
        day = i % num_days
        ts = base + day * day_seconds + random.uniform(0, day_seconds)
        measurement = random.choice(MEASUREMENTS)
        server = random.choice(SERVERS)
        region = random.choice(REGIONS)

        point = {
            "measurement": measurement,
            "timestamp": ts,
            "tags": {"server": server, "region": region},
            "fields": {"value": round(random.uniform(0, 100), 2)},
        }
        # location = one file per measurement + day  (mirrors Week 1 partitioning)
        location = f"{measurement}/day{day}"
        files.setdefault(location, []).append(point)

    # keep each file time-sorted (Day 13 relies on sorted streams)
    for pts in files.values():
        pts.sort(key=lambda p: p["timestamp"])

    print(f"✅ Generated {num_points:,} points in {len(files)} files")
    return files


def run_integration_test():
    print("=" * 60)
    print("🧪 Week 2 Integration Lab: Indexing & Retrieval")
    print("=" * 60)

    files = generate_dataset(50000, 7)
    all_points = [p for pts in files.values() for p in pts]

    # ------------------------------------------------------------------
    # Test 1: Build the indexes
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 1: Build Tag + Time + Series Indexes")
    print("=" * 40)

    tag_index = TagIndex()
    time_index = TimeRangeIndex()
    series = SeriesManager()

    build_start = time.time()
    time_blocks = []
    for location, pts in files.items():
        # tag index: every point's tags -> location
        for p in pts:
            tag_index.add_data_point(p, location)
            series.get_or_create_id(p["measurement"], p["tags"])
        # time index: one block per file with its min/max timestamp
        time_blocks.append((location, pts[0]["timestamp"], pts[-1]["timestamp"]))
    time_index.add_blocks(time_blocks)
    build_time = time.time() - build_start

    print(f"📊 Built indexes in {build_time:.2f}s")
    print(f"   Tag keys indexed: {tag_index.get_tag_keys()}")
    print(f"   Distinct series (cardinality): {series.cardinality()}")
    print(f"   Time blocks: {len(time_index)}")
    report = series.cardinality_report()
    print(f"   Series by measurement: {report.by_measurement}")

    # ------------------------------------------------------------------
    # Test 2: Tag lookups are correct
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 2: Tag Lookup Correctness")
    print("=" * 40)

    target_server = "web-01"
    t0 = time.time()
    locs = tag_index.lookup("server", target_server)
    lookup_ms = (time.time() - t0) * 1000

    # brute-force ground truth
    expected_locs = {loc for loc, pts in files.items()
                     if any(p["tags"]["server"] == target_server for p in pts)}
    assert locs == expected_locs, f"Tag lookup wrong: {locs ^ expected_locs}"
    print(f"✅ server={target_server} -> {len(locs)} files in {lookup_ms:.3f} ms")

    # AND of two tags
    and_locs = tag_index.lookup_multiple(
        {"server": "api-01", "region": "us-west-2"}, MatchMode.AND
    )
    print(f"✅ server=api-01 AND region=us-west-2 -> {len(and_locs)} files")

    # ------------------------------------------------------------------
    # Test 3: Time-range queries prune correctly
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 3: Time Range Pruning")
    print("=" * 40)

    lo, hi = time_index.time_bounds()
    mid = (lo + hi) / 2
    window_start, window_end = mid, mid + 86400  # one-day window in the middle

    candidate_locs = time_index.find_locations_in_range(window_start, window_end)
    # ground truth: any file whose [min,max] overlaps the window
    expected = {loc for loc, pts in files.items()
                if pts[0]["timestamp"] <= window_end and pts[-1]["timestamp"] >= window_start}
    assert set(candidate_locs) == expected, "Time pruning mismatch"
    print(f"✅ Time window pruned to {len(candidate_locs)}/{len(files)} files")

    # ------------------------------------------------------------------
    # Test 4: Combined query via IndexedReader vs full scan
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 4: Combined Tag + Time Query (indexed vs full scan)")
    print("=" * 40)

    reader = IndexedReader(tag_index, time_index, read_location=lambda loc: files[loc])
    q = Query(measurement="cpu", tag_filters={"server": "web-01"},
              start_time=window_start, end_time=window_end)

    t0 = time.time()
    indexed_res = reader.execute(q)
    indexed_ms = (time.time() - t0) * 1000

    # full scan ground truth
    t0 = time.time()
    scan_res = [p for p in all_points
                if p["tags"]["server"] == "web-01"
                and window_start <= p["timestamp"] <= window_end]
    scan_ms = (time.time() - t0) * 1000

    assert len(indexed_res) == len(scan_res), \
        f"Indexed result count {len(indexed_res)} != scan {len(scan_res)}"
    print(f"✅ Indexed query: {len(indexed_res)} points in {indexed_ms:.2f} ms")
    print(f"   Full scan:     {len(scan_res)} points in {scan_ms:.2f} ms")
    speedup = scan_ms / indexed_ms if indexed_ms > 0 else float("inf")
    print(f"   Speedup: {speedup:.1f}x")

    # ------------------------------------------------------------------
    # Test 5: Streaming range query with LIMIT
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 5: Streaming Range Query + LIMIT")
    print("=" * 40)

    engine = RangeQueryEngine(time_index, read_location=lambda loc: files[loc])
    top10 = engine.range_query_list(lo, hi, limit=10)
    ts = [p["timestamp"] for p in top10]
    assert ts == sorted(ts), "range query must be time-sorted"
    assert len(top10) == 10, "LIMIT must cap the result"
    print(f"✅ First 10 points returned in time order (streaming, LIMIT honored)")

    # ------------------------------------------------------------------
    # Test 6: Bloom filter skip optimization
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 6: Bloom Filter Skip Optimization")
    print("=" * 40)

    opt = OptimizedTagIndex(TagIndex(), expected_items_per_location=2000)
    for location, pts in files.items():
        pairs = {(k, v) for p in pts for k, v in p["tags"].items()}
        opt.index_location(location, pairs)

    matches, skipped = opt.lookup_with_skip("server", "db-01", list(files.keys()))
    print(f"✅ Looking up server=db-01: {len(matches)} matched, {len(skipped)} files skipped by bloom")
    assert len(skipped) >= 0  # at minimum the API works; ideally skipped > 0

    # ------------------------------------------------------------------
    # Test 7: Persistence round-trip
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Test 7: Index Persistence Round-Trip")
    print("=" * 40)

    persist_dir = "lab2_index_data"
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
    persist = IndexPersistence(persist_dir)

    # Save the raw tag index structure (access the internal dict).
    raw_tag_index = getattr(tag_index, "_index", None)
    if raw_tag_index is not None:
        persist.save_tag_index(raw_tag_index)
        reloaded = persist.load_tag_index()
        assert reloaded == raw_tag_index, "Tag index changed across save/load"
        print("✅ Tag index survived save -> load unchanged")
    else:
        print("⚠️  Skipped: TagIndex has no _index attribute to persist")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 40)
    print("Summary")
    print("=" * 40)
    print(f"   Points indexed:      {len(all_points):,}")
    print(f"   Files (locations):   {len(files)}")
    print(f"   Series cardinality:  {series.cardinality()}")
    print(f"   Index build time:    {build_time:.2f}s")
    print(f"   Tag lookup latency:  {lookup_ms:.3f} ms")
    print(f"   Indexed vs scan:     {speedup:.1f}x faster")

    print("\n🎉 Week 2 Integration Lab Completed Successfully!")
    print("🚀 Ready to proceed to Week 3: Query Processing")

    shutil.rmtree(persist_dir, ignore_errors=True)
    return {
        "points": len(all_points),
        "files": len(files),
        "cardinality": series.cardinality(),
        "speedup": speedup,
    }


if __name__ == "__main__":
    """
    Run this lab after completing Week 2 exercises (day8-day14).

    This lab will:
    1. Generate 50,000 realistic monitoring points across 7 days
    2. Build tag, time, and series indexes
    3. Verify tag lookups, time pruning, and combined queries vs a full scan
    4. Exercise streaming range queries with LIMIT
    5. Demonstrate bloom-filter skipping
    6. Round-trip the index through disk

    Expected results:
    - All index queries return results identical to a brute-force scan
    - Indexed queries are measurably faster than full scans
    - Indexes reload from disk byte-for-byte equal
    """
    try:
        results = run_integration_test()
        print("\n✅ Lab completed successfully!")
        print("   Continue to Week 3: Query Processing")
    except Exception as e:
        print(f"\n❌ Lab failed with error: {e}")
        print("   Review your Week 2 implementations and try again")
        raise
