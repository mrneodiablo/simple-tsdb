# Week 5 Prompt Template

## 🎯 Quick Copy Prompt for Week 5

```
Hi! Tôi đã hoàn thành Week 1 (Storage), Week 2 (Indexing), Week 3 (Query Processing)
và Week 4 (API Layer) của simple-timeseries-db learning project và muốn tạo
Week 5: Comparison & Analysis.

CONTEXT từ Week 1-4:
- Week 1 (7 exercises): file operations, serialization, line protocol, partitioning,
  write ops, storage manager, compression
- Week 2 (7 exercises): tag index (inverted index), time index (binary search),
  series key management, index persistence, indexed read ops, range queries
  (k-way merge streaming), bloom filter optimization
- Week 3 (7 exercises): filtering (WHERE, AND/OR, predicate pushdown), aggregations
  (sum/count/mean/min/max streaming), percentiles (exact vs histogram), time windows
  (aggregateWindow), group by (hash grouping), query optimization (rule-based plan),
  advanced aggregations (rate/derivative)
- Week 4 (7 exercises): TCP framing, wire protocol, query parser (lexer + recursive
  descent), execution engine, client interface, error handling/validation,
  performance monitoring
- Project structure: simple-timeseries-db/ với exercises/, labs/, src/, docs/
- Learning style: <100 LOC core logic per exercise, leetcode-style problems,
  sequential building
- Approach: Build từ scratch để hiểu concepts, không focus performance

DATA MODEL đã established (giữ nguyên xuyên suốt):
- Data point dạng dict: {"measurement", "timestamp", "tags", "fields"}
- tags = strings only (indexed), fields = any type (not indexed)

FORMAT mỗi exercise (giữ nguyên từ Week 1/2/3/4):
- Module docstring: Problem + Learning Objectives + Real-World Connection
- Imports → dataclasses/Enums → classes với TODO skeleton + raise NotImplementedError
- test_xxx() với 5-8 assert-based test cases + print progress
- __main__ block với Instructions + Success criteria + Next steps
- "Concepts and Theory" block ở cuối file
- Dependencies injected (constructor) để test chạy độc lập bằng fakes

FEEDBACK từ Week 4 implementation:
[Bạn điền feedback về:]
- Code style preference (OOP vs functional, error handling approach)
- Exercises nào quá dễ/khó
- Areas muốn more/less detail
- Algorithms/concepts muốn explore deeper

WEEK 5 REQUIREMENTS (Phase 2 — chỉ 4 exercises, không phải 7):
Tạo 4 exercises cho Comparison & Analysis:
1. Benchmark setup (fair test harness: identical workloads, warmup, repeated trials,
   stats — mean/median/p95/stddev, ops/sec)
2. Write performance (throughput + latency vs batch size, concurrency; your DB numbers)
3. Query performance (point/range/aggregation/group-by scenarios; index vs full scan)
4. Architecture analysis (TSM/TSI vs your approach; trade-off matrix; when-to-use)

Plus 1 integration lab: run the full benchmark suite against your Week 1-4 system and
produce a comparison report.

IMPORTANT constraints (giữ standalone + testable như Week 4):
- Stdlib only (time, statistics, random, dataclasses) — no external deps, no pandas
- InfluxDB KHÔNG bắt buộc phải chạy: so sánh dùng published/reference numbers hoặc
  injected baseline; nếu có InfluxDB thì optional adapter. Tests KHÔNG được cần network
- Benchmarks phải deterministic trong test: inject clock/timer + workload generator
  (seed cố định) để assert được, KHÔNG assert trên wall-clock thật
- Tách "đo" (harness) khỏi "thứ được đo" (target callable) để test bằng fakes

Bạn có thể tạo complete Week 5 với 4 exercises + 1 lab không?
```

## 📝 Feedback Template (Fill After Week 4)

### Technical Preferences:
```
CODE STYLE tôi prefer:
- [ ] OOP classes vs [ ] functional approach
- Error handling: [ ] exceptions vs [ ] return codes vs [ ] mixed
- Data structures: [ ] lists [ ] sets [ ] dicts [ ] custom classes
- Documentation: [ ] detailed docstrings [ ] inline comments [ ] minimal
- Benchmark output: [ ] plain tables [ ] ascii charts [ ] raw numbers + stats

DIFFICULTY LEVEL:
- Week 4 exercises were: [ ] too easy [ ] perfect [ ] too challenging
- I want Week 5 to be: [ ] same level [ ] slightly harder [ ] more detailed
- Focus more on: [ ] methodology/rigor [ ] statistics [ ] architecture analysis
  [ ] practical measurement

LEARNING PREFERENCES:
- Exercises I enjoyed most: day [X], day [Y] because [reason]
- Concepts I want to explore deeper: [list specific topics]
- Areas where I need more explanation: [theory/implementation/examples]
- Time spent per exercise: [X] minutes average
- Preferred exercise length: [ ] current is good [ ] shorter [ ] longer

INFLUXDB COMPARISON:
- [ ] I have InfluxDB running locally and want a real adapter/optional integration
- [ ] Use published/reference numbers only (no live InfluxDB)
- [ ] Focus on architecture/trade-off analysis over head-to-head benchmarks
```

### Implementation Experience:
```
WHAT WORKED WELL:
- [Specific aspects that helped learning]
- [Exercise format preferences]
- [Explanation style that clicked]

WHAT COULD BE IMPROVED:
- [Areas that were confusing]
- [Missing explanations]
- [Suggested adjustments]

CODE QUALITY OBSERVATIONS:
- My typical solution length: [X] lines
- Areas I tend to over-engineer: [list]
- Areas I tend to under-implement: [list]
- Debugging challenges I faced: [list]
```

## 🔄 Alternative Short Prompt

```
Tạo Week 5 (Comparison & Analysis) cho simple-timeseries-db learning project.

Requirements:
- 4 exercises + 1 integration lab (Phase 2 = 4 exercises, not 7)
- Focus: benchmark harness, write performance, query performance, architecture analysis
- Style: <100 LOC core logic, leetcode-style, sequential building
- Include: problem statement, skeleton code (TODO + NotImplementedError), tests, theory
- Stdlib only; inject clock + workload generator (fixed seed) so benchmarks are
  DETERMINISTIC in tests (no asserting on real wall-clock, no network)
- InfluxDB optional: use reference/published numbers or an injected baseline
- Connect to InfluxDB TSM/TSI architecture and benchmarking methodology

Project context: Week 1-4 built a working TSDB (storage, indexing, query engine, API).
Week 5 measures it rigorously and compares design trade-offs against InfluxDB.

Create complete exercises following same format as established curriculum.
```

## 📚 Project Context Reference

### Established Structure:
```
simple-timeseries-db/
├── README.md (project overview)
├── CURRICULUM.md (6-week plan)
├── CONCEPTS.md (theory explanations)
├── exercises/week1_storage/ (7 completed exercises)
├── exercises/week2_indexing/ (7 completed exercises)
├── exercises/week3_querying/ (7 completed exercises)
├── exercises/week4_api/ (7 completed exercises)
├── labs/week1_lab.py .. week4_lab.py (integration tests)
├── benchmarks/ (write/read/compare — Week 5 lands here too)
├── src/tsdb/ (source modules: storage/, index/, query/, server/)
├── requirements.txt (minimal dependencies)
```

### Week 1 Achievements:
- ✅ File operations & directory structure
- ✅ JSON serialization with type preservation
- ✅ Line protocol parsing with validation
- ✅ Time-based partitioning strategies
- ✅ Batch write operations with atomicity
- ✅ Unified storage manager interface
- ✅ Basic compression (Delta, RLE, Gorilla)

### Week 2 Achievements:
- ✅ Hash-based tag index (inverted index, AND/OR posting lists)
- ✅ Time range index (binary search via bisect, interval overlap)
- ✅ Series key management (canonical keys, escaping, cardinality tracking)
- ✅ Index persistence (atomic writes, snapshot + incremental log, versioning)
- ✅ Indexed read operations (query planner: tag ∩ time, predicate pushdown)
- ✅ Range query optimization (streaming k-way merge, LIMIT, O(k) memory)
- ✅ Bloom filter optimization (no false negatives, file-skip)

### Week 3 Achievements:
- ✅ Basic filtering (predicate tree, comparison ops, AND/OR, predicate pushdown split)
- ✅ Aggregation functions (streaming sum/count/mean/min/max, Welford, null handling)
- ✅ Percentiles (exact interpolation vs bounded-memory histogram)
- ✅ Time window operations (aggregateWindow, epoch alignment, empty-window fill)
- ✅ Group by (hash grouping, tuple keys, group + window composite key)
- ✅ Query optimization (rule-based plan: merge/pushdown/reorder, cost model)
- ✅ Advanced aggregations (rate/derivative, per-second normalization, counter resets)

### Week 4 Achievements:
- ✅ TCP server foundation (length-prefixed framing, stateful decoder, connection loop)
- ✅ Protocol design (versioned TSDB/1 request/response, status+code+body, errors)
- ✅ Query parser (lexer + recursive descent -> typed AST)
- ✅ Query execution engine (read -> filter -> group -> aggregate, injected data source)
- ✅ Client interface (framing round-trip, ping/write/query, ServerError, table format)
- ✅ Error handling & validation (400/404/422/500 taxonomy, total handler, sanitized 500)
- ✅ Performance monitoring (injected clock, per-op count/latency/p95/throughput)

### Week 5 Goals:
- Measure the Week 1-4 system rigorously with a fair, repeatable benchmark harness
- Quantify write throughput/latency across batch sizes and concurrency
- Quantify query performance across scenarios; show index vs full-scan speedups
- Analyze architecture trade-offs vs InfluxDB (TSM storage, TSI indexing)
- Produce a comparison report with honest conclusions about design choices

### Day-by-Day (from CURRICULUM.md — Phase 2 has 4 exercises):
- Day 29: Benchmark Setup            → exercises/week5_comparison/day29_benchmark_setup.py
- Day 30: Write Performance          → exercises/week5_comparison/day30_write_benchmark.py
- Day 31: Query Performance Analysis  → exercises/week5_comparison/day31_query_benchmark.py
- Day 32: Architecture Deep Dive      → exercises/week5_comparison/day32_architecture_analysis.py
- Lab:    labs/week5_lab.py

### Testability Notes (carry forward from Week 4):
- Benchmarks must be DETERMINISTIC under test. Inject a timer/clock (a fake that
  returns scripted durations) and a workload generator seeded with a fixed value, so
  tests assert on computed statistics (mean/median/p95/stddev, ops/sec) — never on real
  wall-clock time.
- Separate the HARNESS (times a callable, repeats trials, aggregates stats) from the
  TARGET (the thing measured). Unit tests point the harness at a fake target with known
  behavior; the lab points it at the real Week 1-4 system.
- No network / no InfluxDB in unit tests. Comparison against InfluxDB uses published or
  injected baseline numbers; a live InfluxDB adapter (if the user has one) is optional
  and only touched in the lab.
- Reuse earlier building blocks: the p95/percentile math (Week 3 Day 17) and the
  metrics collector (Week 4 Day 28) — don't reinvent statistics.

## 💡 Usage Instructions

1. **Complete Week 4** exercises first (day22-day28 + week4_lab)
2. **Fill feedback template** based on implementation experience
3. **Copy main prompt** and paste feedback section
4. **Start new Claude session** (or continue this one) and paste complete prompt
5. **Get Week 5 exercises** tailored to your learning style

## 🎯 Success Metrics

Week 5 should deliver:
- [ ] 4 progressive exercises building a benchmark + analysis toolkit
- [ ] Each exercise <100 LOC core logic with comprehensive tests
- [ ] Integration lab: full benchmark suite over the Week 1-4 system + comparison report
- [ ] Deterministic, stdlib-only, no-network tests (injected clock + seeded workload)
- [ ] Clear connections to InfluxDB TSM/TSI architecture and benchmarking methodology
- [ ] Difficulty level appropriate to your feedback
- [ ] Code style matching your preferences

---

**File Location**: `docs/WEEK5_PROMPT_TEMPLATE.md`

**Last Updated**: July 2026
**Usage**: Copy prompt sections as needed for Week 5 creation
