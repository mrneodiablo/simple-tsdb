# Week 3 Prompt Template

## 🎯 Quick Copy Prompt for Week 3

```
Hi! Tôi đã hoàn thành Week 1 (Storage) và Week 2 (Indexing) của simple-timeseries-db
learning project và muốn tạo Week 3: Query Processing.

CONTEXT từ Week 1 + 2:
- Week 1 (7 exercises): file operations, serialization, line protocol, partitioning,
  write ops, storage manager, compression
- Week 2 (7 exercises): tag index (inverted index), time index (binary search),
  series key management, index persistence, indexed read ops, range queries
  (k-way merge streaming), bloom filter optimization
- Project structure: simple-timeseries-db/ với exercises/, labs/, src/, docs/
- Learning style: <100 LOC core logic per exercise, leetcode-style problems,
  sequential building
- Approach: Build từ scratch để hiểu concepts, không focus performance

DATA MODEL đã established (giữ nguyên xuyên suốt):
- Data point dạng dict: {"measurement", "timestamp", "tags", "fields"}
- tags = strings only (indexed), fields = any type (not indexed)

FORMAT mỗi exercise (giữ nguyên từ Week 1/2):
- Module docstring: Problem + Learning Objectives + Real-World Connection
- Imports → dataclasses/Enums → classes với TODO skeleton + raise NotImplementedError
- test_xxx() với 5-8 assert-based test cases + print progress
- __main__ block với Instructions + Success criteria + Next steps
- "Concepts and Theory" block ở cuối file
- Dependencies injected (constructor) để test chạy độc lập bằng fakes

FEEDBACK từ Week 2 implementation:
[Bạn điền feedback về:]
- Code style preference (OOP vs functional, error handling approach)
- Exercises nào quá dễ/khó
- Areas muốn more/less detail
- Algorithms/concepts muốn explore deeper

WEEK 3 REQUIREMENTS:
Tạo 7 exercises cho Query Processing:
1. Basic filtering (WHERE clause: AND/OR, comparison operators, predicate pushdown)
2. Aggregation functions (sum, count, mean, min, max — streaming, null handling)
3. Percentile calculations (p50/p95/p99 — exact vs approximate)
4. Time window operations (aggregateWindow: 5m/1h buckets, alignment)
5. Group by operations (group by tag values, hash-based grouping)
6. Query optimization (execution plan, filter pushdown, operation reordering)
7. Advanced aggregations (rate, derivatives, counter reset handling)

Plus 1 integration lab testing full query engine.

Bạn có thể tạo complete Week 3 với 7 exercises + 1 lab không?
```

## 📝 Feedback Template (Fill After Week 2)

### Technical Preferences:
```
CODE STYLE tôi prefer:
- [ ] OOP classes vs [ ] functional approach
- Error handling: [ ] exceptions vs [ ] return codes vs [ ] mixed
- Data structures: [ ] lists [ ] sets [ ] dicts [ ] custom classes
- Documentation: [ ] detailed docstrings [ ] inline comments [ ] minimal

DIFFICULTY LEVEL:
- Week 2 exercises were: [ ] too easy [ ] perfect [ ] too challenging
- I want Week 3 to be: [ ] same level [ ] slightly harder [ ] more detailed
- Focus more on: [ ] algorithms [ ] theory [ ] practical implementation

LEARNING PREFERENCES:
- Exercises I enjoyed most: day [X], day [Y] because [reason]
- Concepts I want to explore deeper: [list specific topics]
- Areas where I need more explanation: [theory/implementation/examples]
- Time spent per exercise: [X] minutes average
- Preferred exercise length: [ ] current is good [ ] shorter [ ] longer
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
Tạo Week 3 (Query Processing) cho simple-timeseries-db learning project.

Requirements:
- 7 exercises + 1 integration lab
- Focus: filtering, aggregations, percentiles, time windows, group by,
  query optimization, rate/derivatives
- Style: <100 LOC core logic, leetcode-style, sequential building
- Include: problem statement, skeleton code (TODO + NotImplementedError), tests, theory
- Inject dependencies so each exercise tests independently with fakes
- Connect to InfluxDB / Flux architecture

Project context: Week 1 storage, Week 2 indexing done. Week 3 builds the query
engine that filters and aggregates the data the indexes locate.

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
├── labs/week1_lab.py, labs/week2_lab.py (integration tests)
├── src/tsdb/ (source modules)
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

### Week 3 Goals:
- Build the query engine on top of storage + indexes
- Implement filtering (WHERE) with boolean logic and predicate pushdown
- Implement statistical aggregations (sum/count/mean/min/max) — streaming
- Calculate percentiles (p50/p95/p99) accurately and memory-efficiently
- Group data into time windows (aggregateWindow)
- Group results by tag values (GROUP BY)
- Build a small query optimizer (execution plan, operation reordering)
- Implement rate / derivative functions with counter-reset handling

### Day-by-Day (from CURRICULUM.md):
- Day 15: Basic Filtering        → exercises/week3_querying/day15_basic_filtering.py
- Day 16: Aggregation Functions  → exercises/week3_querying/day16_aggregations.py
- Day 17: Percentile Calculations→ exercises/week3_querying/day17_percentiles.py
- Day 18: Time Window Operations → exercises/week3_querying/day18_time_windows.py
- Day 19: Group By Operations    → exercises/week3_querying/day19_groupby.py
- Day 20: Query Optimization     → exercises/week3_querying/day20_optimization.py
- Day 21: Advanced Aggregations  → exercises/week3_querying/day21_advanced_agg.py
- Lab:    labs/week3_lab.py

## 💡 Usage Instructions

1. **Complete Week 2** exercises first (day8-day14 + week2_lab)
2. **Fill feedback template** based on implementation experience
3. **Copy main prompt** and paste feedback section
4. **Start new Claude session** (or continue this one) and paste complete prompt
5. **Get Week 3 exercises** tailored to your learning style

## 🎯 Success Metrics

Week 3 should deliver:
- [ ] 7 progressive exercises building the query engine
- [ ] Each exercise <100 LOC core logic with comprehensive tests
- [ ] Integration lab testing full query functionality
- [ ] Clear connections to InfluxDB / Flux architecture
- [ ] Difficulty level appropriate to your feedback
- [ ] Code style matching your preferences

---

**File Location**: `/Users/dongvothanh/Data/learning/influxdb_course/simple-timeseries-db/WEEK3_PROMPT_TEMPLATE.md`

**Last Updated**: June 2026
**Usage**: Copy prompt sections as needed for Week 3 creation
