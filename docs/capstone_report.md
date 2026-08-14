# simple-timeseries-db — 6-Week Capstone Report

## Overview

Built a time-series database from scratch over six weeks:
storage, indexing, query engine, API layer, benchmarking, and analysis.

## Key Results

| Metric | Value |
| --- | --- |
| dataset points | 20000 |
| top bottleneck | scan_query (98%) |
| optimization speedup | 7678x |
| optimization correct | True |

## Quick Wins for Production

- Write throughput: raise client batch size (see Week 5 amortization curve)
- Slow InfluxDB point queries: ensure selective tags are indexed / avoid full-measurement scans

## Conclusion

Indexing selective lookups and batching writes deliver the biggest,
cheapest wins — verified by profiling and a correctness-guarded benchmark.
