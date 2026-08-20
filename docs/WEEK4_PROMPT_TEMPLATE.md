# Week 4 Prompt Template

## 🎯 Quick Copy Prompt for Week 4

```
Hi! Tôi đã hoàn thành Week 1 (Storage), Week 2 (Indexing) và Week 3 (Query Processing)
của simple-timeseries-db learning project và muốn tạo Week 4: API Layer.

CONTEXT từ Week 1 + 2 + 3:
- Week 1 (7 exercises): file operations, serialization, line protocol, partitioning,
  write ops, storage manager, compression
- Week 2 (7 exercises): tag index (inverted index), time index (binary search),
  series key management, index persistence, indexed read ops, range queries
  (k-way merge streaming), bloom filter optimization
- Week 3 (7 exercises): basic filtering (WHERE, AND/OR, predicate pushdown),
  aggregations (sum/count/mean/min/max streaming), percentiles (exact vs histogram),
  time windows (aggregateWindow, epoch alignment), group by (hash grouping),
  query optimization (rule-based execution plan), advanced aggregations (rate/derivative)
- Project structure: simple-timeseries-db/ với exercises/, labs/, src/, docs/
- Learning style: <100 LOC core logic per exercise, leetcode-style problems,
  sequential building
- Approach: Build từ scratch để hiểu concepts, không focus performance

DATA MODEL đã established (giữ nguyên xuyên suốt):
- Data point dạng dict: {"measurement", "timestamp", "tags", "fields"}
- tags = strings only (indexed), fields = any type (not indexed)

FORMAT mỗi exercise (giữ nguyên từ Week 1/2/3):
- Module docstring: Problem + Learning Objectives + Real-World Connection
- Imports → dataclasses/Enums → classes với TODO skeleton + raise NotImplementedError
- test_xxx() với 5-8 assert-based test cases + print progress
- __main__ block với Instructions + Success criteria + Next steps
- "Concepts and Theory" block ở cuối file
- Dependencies injected (constructor) để test chạy độc lập bằng fakes

FEEDBACK từ Week 3 implementation:
[Bạn điền feedback về:]
- Code style preference (OOP vs functional, error handling approach)
- Exercises nào quá dễ/khó
- Areas muốn more/less detail
- Algorithms/concepts muốn explore deeper

WEEK 4 REQUIREMENTS:
Tạo 7 exercises cho API Layer:
1. TCP server foundation (socket, concurrent connections, framing)
2. Protocol design (text-based request/response, versioning, error frames)
3. Query parser (lexer + recursive descent: SELECT / FROM / WHERE / GROUP BY)
4. Query execution engine (bind parsed query -> Week 2 indexes + Week 3 operators)
5. Client interface (connection mgmt, write/query API, result formatting)
6. Error handling & validation (input validation, error taxonomy, graceful failure)
7. Performance monitoring (per-query metrics, latency/throughput, low overhead)

Plus 1 integration lab testing full system via TCP client (write -> query -> result).

IMPORTANT constraints (giữ standalone + testable như Week 3):
- Prefer stdlib only (socket, socketserver, threading, selectors) — no external deps
- Inject dependencies (storage/index/query engine, clock, socket factory) để test
  bằng fakes, KHÔNG cần mở real socket trong unit tests
- Tests phải chạy được ngay cả khi Week 1-3 chưa hoàn chỉnh (dùng fakes/in-memory)

Bạn có thể tạo complete Week 4 với 7 exercises + 1 lab không?
```

## 📝 Feedback Template (Fill After Week 3)

### Technical Preferences:
```
CODE STYLE tôi prefer:
- [ ] OOP classes vs [ ] functional approach
- Error handling: [ ] exceptions vs [ ] return codes vs [ ] mixed
- Data structures: [ ] lists [ ] sets [ ] dicts [ ] custom classes
- Documentation: [ ] detailed docstrings [ ] inline comments [ ] minimal
- Concurrency: [ ] threads [ ] asyncio [ ] selectors/single-thread [ ] don't care

DIFFICULTY LEVEL:
- Week 3 exercises were: [ ] too easy [ ] perfect [ ] too challenging
- I want Week 4 to be: [ ] same level [ ] slightly harder [ ] more detailed
- Focus more on: [ ] algorithms [ ] theory [ ] practical implementation [ ] networking

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
Tạo Week 4 (API Layer) cho simple-timeseries-db learning project.

Requirements:
- 7 exercises + 1 integration lab
- Focus: TCP server, protocol design, query parser, execution engine,
  client interface, error handling, performance monitoring
- Style: <100 LOC core logic, leetcode-style, sequential building
- Include: problem statement, skeleton code (TODO + NotImplementedError), tests, theory
- Stdlib only (socket/socketserver/threading/selectors); inject dependencies so each
  exercise tests independently with fakes (no real socket needed in unit tests)
- Connect to InfluxDB HTTP API / InfluxQL / Flux architecture

Project context: Week 1 storage, Week 2 indexing, Week 3 query engine done. Week 4
exposes the query engine over the network: parse a query, execute it against the
indexes + operators, return results to a client.

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
├── labs/week1_lab.py, week2_lab.py, week3_lab.py (integration tests)
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

### Week 4 Goals:
- Expose the query engine over the network (client/server boundary)
- Build a concurrent TCP server with a message-framed protocol
- Design a simple text protocol (request/response, errors, versioning)
- Parse a SQL-like query language (lexer + recursive descent -> AST)
- Bind the parsed query to Week 2 indexes + Week 3 operators (execution engine)
- Provide a client library (connect, write, query, format results)
- Add robust error handling/validation and lightweight performance monitoring

### Day-by-Day (from CURRICULUM.md):
- Day 22: TCP Server Foundation   → exercises/week4_api/day22_tcp_server.py
- Day 23: Protocol Design         → exercises/week4_api/day23_protocol.py
- Day 24: Query Parser            → exercises/week4_api/day24_query_parser.py
- Day 25: Query Execution Engine  → exercises/week4_api/day25_execution_engine.py
- Day 26: Client Interface        → exercises/week4_api/day26_client.py
- Day 27: Error Handling & Validation → exercises/week4_api/day27_error_handling.py
- Day 28: Performance Monitoring  → exercises/week4_api/day28_monitoring.py
- Lab:    labs/week4_lab.py

### Testability Notes (carry forward from Week 3):
- Unit tests must NOT depend on binding a real port. Test protocol parsing/framing on
  bytes/strings, test the execution engine against in-memory fakes, and test the
  server's request handler as a pure function (bytes in -> bytes out) where possible.
- Inject: a socket/transport factory, a clock (for monitoring/latency), and the
  query engine, so each exercise runs green in isolation.
- The integration lab (labs/week4_lab.py) is the ONE place a real loopback socket is
  acceptable — start the server on 127.0.0.1:0 (ephemeral port) in a thread, run a
  client round-trip, then shut it down cleanly.

## 💡 Usage Instructions

1. **Complete Week 3** exercises first (day15-day21 + week3_lab)
2. **Fill feedback template** based on implementation experience
3. **Copy main prompt** and paste feedback section
4. **Start new Claude session** (or continue this one) and paste complete prompt
5. **Get Week 4 exercises** tailored to your learning style

## 🎯 Success Metrics

Week 4 should deliver:
- [ ] 7 progressive exercises building the API layer
- [ ] Each exercise <100 LOC core logic with comprehensive tests
- [ ] Integration lab: full write -> query -> result round-trip over a real loopback socket
- [ ] Stdlib-only, dependency-injected, unit-testable without opening ports
- [ ] Clear connections to InfluxDB HTTP API / InfluxQL / Flux
- [ ] Difficulty level appropriate to your feedback
- [ ] Code style matching your preferences

---

**File Location**: `docs/WEEK4_PROMPT_TEMPLATE.md`

**Last Updated**: July 2026
**Usage**: Copy prompt sections as needed for Week 4 creation
