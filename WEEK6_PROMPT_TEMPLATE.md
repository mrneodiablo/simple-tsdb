# Week 6 Prompt Template

## 🎯 Quick Copy Prompt for Week 6

```
Hi! Tôi đã hoàn thành Week 1-5 của simple-timeseries-db learning project và muốn tạo
Week 6: Production Application (tuần cuối cùng — capstone).

CONTEXT từ Week 1-5:
- Week 1 (7 exercises): file operations, serialization, line protocol, partitioning,
  write ops, storage manager, compression
- Week 2 (7 exercises): tag index (inverted index), time index (binary search),
  series key management, index persistence, indexed read ops, range queries
  (k-way merge streaming), bloom filter optimization
- Week 3 (7 exercises): filtering (WHERE, AND/OR, predicate pushdown), aggregations
  (streaming), percentiles (exact vs histogram), time windows (aggregateWindow),
  group by (hash grouping), query optimization (rule-based plan), rate/derivative
- Week 4 (7 exercises): TCP framing, wire protocol, query parser (lexer + recursive
  descent), execution engine, client interface, error handling/validation, monitoring
- Week 5 (4 exercises): benchmark harness, write performance, query performance,
  architecture analysis (trade-off matrix + recommender)
- Project structure: simple-timeseries-db/ với exercises/, labs/, src/, docs/
- Learning style: <100 LOC core logic per exercise, leetcode-style problems,
  sequential building
- Approach: Build từ scratch để hiểu concepts, không focus performance

DATA MODEL đã established (giữ nguyên xuyên suốt):
- Data point dạng dict: {"measurement", "timestamp", "tags", "fields"}
- tags = strings only (indexed), fields = any type (not indexed)

FORMAT mỗi exercise (giữ nguyên từ Week 1-5):
- Module docstring: Problem + Learning Objectives + Real-World Connection
- Imports → dataclasses/Enums → classes với TODO skeleton + raise NotImplementedError
- test_xxx() với 5-8 assert-based test cases + print progress
- __main__ block với Instructions + Success criteria + Next steps
- "Concepts and Theory" block ở cuối file
- Dependencies injected (constructor) để test chạy độc lập bằng fakes

FEEDBACK từ Week 5 implementation:
[Bạn điền feedback về:]
- Code style preference (OOP vs functional, error handling approach)
- Exercises nào quá dễ/khó
- Areas muốn more/less detail
- Algorithms/concepts muốn explore deeper

WEEK 6 REQUIREMENTS (Phase 2 — chỉ 4 exercises, không phải 7):
Tạo 4 exercises cho Production Application (capstone tuần cuối):
1. Bottleneck identification (profiling: hotspot ranking từ per-operation timings,
   Amdahl's law — optimizing thứ nào đáng, cumulative %)
2. Production optimization (before/after measurement, regression guard, chứng minh
   improvement mà giữ correctness)
3. Real-world application (mapping framework: work system challenge -> learning ->
   recommendation, prioritized bằng impact/effort)
4. Knowledge documentation (structured report/blog generator: findings -> markdown,
   consistent sections)

Plus 1 final lab: capstone demonstration — chạy toàn bộ hệ thống Week 1-5, profile nó,
áp một optimization, đo lại, và sinh ra final report (markdown).

IMPORTANT constraints (giữ standalone + testable như Week 5):
- Stdlib only (time, statistics, dataclasses, textwrap) — no external deps
- Deterministic tests: inject clock/profiler samples + fixed inputs; KHÔNG assert
  trên wall-clock thật, KHÔNG network
- Tách "đo/phân tích" (framework) khỏi "dữ liệu được phân tích" (injected samples)
- Tái sử dụng: MetricsCollector (Week 4 Day 28), Benchmark harness (Week 5 Day 29),
  percentile math (Week 3 Day 17) — đừng viết lại
- Documentation exercise sinh string/markdown thuần (assert được), KHÔNG ghi file
  bắt buộc trong unit test

Bạn có thể tạo complete Week 6 với 4 exercises + 1 final lab không?
```

## 📝 Feedback Template (Fill After Week 5)

### Technical Preferences:
```
CODE STYLE tôi prefer:
- [ ] OOP classes vs [ ] functional approach
- Error handling: [ ] exceptions vs [ ] return codes vs [ ] mixed
- Data structures: [ ] lists [ ] sets [ ] dicts [ ] custom classes
- Documentation: [ ] detailed docstrings [ ] inline comments [ ] minimal
- Report output: [ ] markdown [ ] plain text tables [ ] structured dict/JSON

DIFFICULTY LEVEL:
- Week 5 exercises were: [ ] too easy [ ] perfect [ ] too challenging
- I want Week 6 to be: [ ] same level [ ] slightly harder [ ] more detailed
- Focus more on: [ ] profiling/optimization [ ] applied/real-world [ ] communication
  [ ] synthesis of the whole project

LEARNING PREFERENCES:
- Exercises I enjoyed most: day [X], day [Y] because [reason]
- Concepts I want to explore deeper: [list specific topics]
- Areas where I need more explanation: [theory/implementation/examples]
- Time spent per exercise: [X] minutes average
- Preferred exercise length: [ ] current is good [ ] shorter [ ] longer

CAPSTONE FOCUS:
- Real work system I want to apply learnings to: [InfluxDB in prod / other DB / none]
- Deliverable I care most about: [ ] blog post [ ] internal doc [ ] team talk
  [ ] just the working system
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
Tạo Week 6 (Production Application — capstone) cho simple-timeseries-db learning project.

Requirements:
- 4 exercises + 1 final lab (Phase 2 = 4 exercises, not 7)
- Focus: bottleneck identification/profiling, production optimization (before/after +
  regression guard), real-world application mapping, knowledge documentation
- Style: <100 LOC core logic, leetcode-style, sequential building
- Include: problem statement, skeleton code (TODO + NotImplementedError), tests, theory
- Stdlib only; inject profiler samples + clock so analysis is DETERMINISTIC in tests
  (no real wall-clock asserts, no network); reuse Week 4 metrics + Week 5 harness
- Documentation exercise produces markdown strings (assertable), no mandatory file I/O
- Connect to InfluxDB production tuning & how databases evolve

Project context: Week 1-5 built and benchmarked a working TSDB. Week 6 profiles it,
optimizes a bottleneck with proof, applies the learnings to a real work system, and
documents the whole journey.

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
├── exercises/week5_comparison/ (4 completed exercises)
├── labs/week1_lab.py .. week5_lab.py (integration tests)
├── benchmarks/ (write/read/compare)
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

### Week 5 Achievements:
- ✅ Benchmark harness (injected timer, warmup, trials, mean/median/p95/stddev, speedup)
- ✅ Write performance (seeded workload, throughput vs batch size, amortization curve)
- ✅ Query performance (indexed vs full-scan speedup per query shape, selectivity)
- ✅ Architecture analysis (scored dimensions, workload weights, recommender + matrix)

### Week 6 Goals:
- Profile the Week 1-5 system and rank bottlenecks by real impact (Amdahl's law)
- Optimize the top bottleneck with before/after proof + a regression guard on correctness
- Map the learnings onto a real work system as prioritized recommendations (impact/effort)
- Document the whole 6-week journey as a structured report / blog post
- Capstone: end-to-end demonstration + generated final report

### Day-by-Day (from CURRICULUM.md — Phase 2 has 4 exercises):
- Day 33: Bottleneck Identification → exercises/week6_production/day33_bottleneck_analysis.py
- Day 34: Production Optimization   → exercises/week6_production/day34_optimization.py
- Day 35: Real-World Application    → exercises/week6_production/day35_work_application.py
- Day 36: Knowledge Documentation   → exercises/week6_production/day36_documentation.py
- Lab:    labs/week6_lab.py  (final capstone demonstration)

### Testability Notes (carry forward from Week 5):
- All analysis must be DETERMINISTIC under test. Inject profiler samples / per-operation
  timings and a fake clock; assert on computed rankings, percentages, and speedups —
  never on real wall-clock time, never over the network.
- Separate the FRAMEWORK (profiles, ranks, optimizes, documents) from the DATA (injected
  timing samples, a before/after pair, a fixed case study). Unit tests feed known data;
  the lab feeds the real Week 1-5 system.
- Reuse existing building blocks — do NOT reinvent:
    * MetricsCollector / per-op stats (Week 4 Day 28)
    * Benchmark harness + speedup (Week 5 Day 29)
    * percentile interpolation (Week 3 Day 17)
    * ArchitectureComparison (Week 5 Day 32) for the applied recommendation
- The documentation exercise returns markdown STRINGS that tests assert on (headers,
  sections, embedded numbers). Writing to disk is optional and only in the lab.
- The Day 34 optimization must keep a CORRECTNESS check (optimized output == baseline
  output on the same input) alongside the speed measurement — faster-but-wrong fails.

## 💡 Usage Instructions

1. **Complete Week 5** exercises first (day29-day32 + week5_lab)
2. **Fill feedback template** based on implementation experience
3. **Copy main prompt** and paste feedback section
4. **Start new Claude session** (or continue this one) and paste complete prompt
5. **Get Week 6 exercises** tailored to your learning style

## 🎯 Success Metrics

Week 6 should deliver:
- [ ] 4 progressive exercises: profile -> optimize -> apply -> document
- [ ] Each exercise <100 LOC core logic with comprehensive tests
- [ ] Final capstone lab: run the whole system, optimize with proof, generate a report
- [ ] Deterministic, stdlib-only, no-network tests (injected samples + clock)
- [ ] Optimization proven faster AND still correct (regression guard)
- [ ] Clear connections to InfluxDB production tuning and how databases evolve
- [ ] Difficulty level appropriate to your feedback
- [ ] A shareable artifact (markdown report) synthesizing the 6-week journey

---

**File Location**: `/Users/dongvothanh/Data/mrneodiablo/simple-tsdb/WEEK6_PROMPT_TEMPLATE.md`

**Last Updated**: July 2026
**Usage**: Copy prompt sections as needed for Week 6 creation
