# 6-Week Time-Series Database Curriculum

## 📋 Overview

**Total Duration**: 6 weeks
**Time Investment**: 3-4 hours per week
**Exercise Format**: Leetcode-style problems with database focus
**Integration Labs**: Weekly hands-on testing

## 🎯 Learning Progression

```
Week 1-4: Core Implementation (Build from scratch)
Week 5-6: Real-world Application (Compare and optimize)
```

---

## 📅 Week 1: Storage Foundation

**Goal**: Build basic file-based storage system for time-series data

### Day 1: File Operations & Data Structures
**File**: `exercises/week1_storage/day1_file_operations.py`

**Problem**: Implement basic file operations for time-series data storage
```python
# Input: Time-series data points
# Output: Organized file structure
# Requirements: Create, read, write, append operations
```

**Concepts Covered**:
- File I/O in Python
- Directory structure for time-series data
- Error handling for file operations

**InfluxDB Connection**: How InfluxDB organizes TSM files on disk

---

### Day 2: Data Serialization
**File**: `exercises/week1_storage/day2_serialization.py`

**Problem**: Convert time-series data to/from JSON format
```python
# Input: Python objects (measurement, tags, fields, timestamp)
# Output: JSON string and reverse parsing
# Requirements: Handle different field types (int, float, string, bool)
```

**Concepts Covered**:
- JSON serialization/deserialization
- Data type handling
- Schema flexibility

**InfluxDB Connection**: Line Protocol vs JSON serialization trade-offs

---

### Day 3: Line Protocol Parser
**File**: `exercises/week1_storage/day3_line_protocol.py`

**Problem**: Parse InfluxDB line protocol format
```python
# Input: "cpu,host=server1 usage=23.5,idle=76.5 1234567890"
# Output: Structured data object
# Requirements: Handle tags, fields, timestamps, escaping
```

**Concepts Covered**:
- String parsing and tokenization
- Protocol design principles
- Error handling for malformed data

**InfluxDB Connection**: Understanding InfluxDB's line protocol design decisions

---

### Day 4: Time-Based Partitioning
**File**: `exercises/week1_storage/day4_partitioning.py`

**Problem**: Organize data files by time ranges (hourly, daily)
```python
# Input: Time-series points with timestamps
# Output: Files organized by time buckets
# Requirements: Configurable time intervals, efficient lookups
```

**Concepts Covered**:
- Time-based data partitioning
- File naming conventions
- Configurable retention policies

**InfluxDB Connection**: How InfluxDB organizes shards by time

**Mini Checkpoint**: Test writing 100 points to different time partitions

---

### Day 5: Write Operations
**File**: `exercises/week1_storage/day5_write_ops.py`

**Problem**: Implement efficient batch write operations
```python
# Input: List of data points
# Output: Persisted to appropriate files
# Requirements: Batch processing, atomic writes, error recovery
```

**Concepts Covered**:
- Batch processing for efficiency
- Atomic operations
- Write-ahead logging concept

**InfluxDB Connection**: WAL (Write-Ahead Log) in InfluxDB

---

### Day 6: Storage Manager
**File**: `exercises/week1_storage/day6_storage_manager.py`

**Problem**: Create unified storage interface
```python
# Input: High-level storage operations
# Output: Coordinate file operations, partitioning, serialization
# Requirements: Clean API, error handling, configuration
```

**Concepts Covered**:
- Interface design
- Component coordination
- Configuration management

**Mini Checkpoint**: Test storage manager with 1000+ points

---

### Day 7: Data Compression Basics
**File**: `exercises/week1_storage/day7_compression.py`

**Problem**: Implement simple compression for time-series data
```python
# Input: Time-series data with patterns
# Output: Compressed storage format
# Requirements: Delta encoding for timestamps, simple field compression
```

**Concepts Covered**:
- Delta encoding
- Run-length encoding
- Compression trade-offs

**InfluxDB Connection**: How TSM files achieve compression

---

### Week 1 Integration Lab
**File**: `labs/week1_lab.py`

**Test Scenario**:
- Write 10,000 time-series points
- Verify file organization
- Test different time ranges
- Measure storage efficiency
- Validate data integrity

**Success Criteria**:
- All data persisted correctly
- Files organized by time partitions
- Basic compression working
- No data corruption

---

## 📅 Week 2: Indexing & Retrieval

**Goal**: Build indexing system for fast queries

### Day 8: Hash-Based Tag Indexing
**File**: `exercises/week2_indexing/day8_tag_index.py`

**Problem**: Create hash index for tag-based queries
```python
# Input: Tag key-value pairs from stored data
# Output: Hash index for O(1) tag lookups
# Requirements: Handle multiple tag combinations
```

**Concepts Covered**:
- Hash table implementation
- Index key design
- Memory vs disk trade-offs

**InfluxDB Connection**: TSI (Time Series Index) in InfluxDB

---

### Day 9: Time Range Indexing
**File**: `exercises/week2_indexing/day9_time_index.py`

**Problem**: Implement time-based index using binary search
```python
# Input: Time ranges from queries
# Output: Efficient file/partition lookup
# Requirements: Binary search on sorted time ranges
```

**Concepts Covered**:
- Binary search algorithms
- Time range queries
- Index maintenance

**InfluxDB Connection**: How InfluxDB handles time range queries

---

### Day 10: Series Key Management
**File**: `exercises/week2_indexing/day10_series_keys.py`

**Problem**: Manage unique series identifiers
```python
# Input: Measurement + tag combinations
# Output: Unique series keys and reverse lookups
# Requirements: Efficient series enumeration, cardinality tracking
```

**Concepts Covered**:
- Series key generation
- Cardinality management
- Memory-efficient storage

**InfluxDB Connection**: Series cardinality and memory usage

**Mini Checkpoint**: Test indexing 1000+ unique series

---

### Day 11: Index Persistence
**File**: `exercises/week2_indexing/day11_index_persistence.py`

**Problem**: Save and load indexes from disk
```python
# Input: In-memory indexes
# Output: Persistent index files
# Requirements: Fast loading, incremental updates
```

**Concepts Covered**:
- Index serialization
- Incremental updates
- Index rebuilding strategies

**InfluxDB Connection**: How InfluxDB persists and loads indexes

---

### Day 12: Read Operations
**File**: `exercises/week2_indexing/day12_read_ops.py`

**Problem**: Implement efficient data retrieval using indexes
```python
# Input: Query with tag filters and time range
# Output: Matching data points
# Requirements: Use indexes for fast lookups
```

**Concepts Covered**:
- Query execution planning
- Index utilization
- Result set optimization

**InfluxDB Connection**: Query execution in InfluxDB

---

### Day 13: Range Queries
**File**: `exercises/week2_indexing/day13_range_queries.py`

**Problem**: Optimize queries over time ranges
```python
# Input: Start time, end time, optional tag filters
# Output: All matching points in time order
# Requirements: Efficient time-based scanning
```

**Concepts Covered**:
- Range scan algorithms
- Iterator patterns
- Memory-efficient processing

**Mini Checkpoint**: Query 100K points with various time ranges

---

### Day 14: Index Optimization
**File**: `exercises/week2_indexing/day14_index_optimization.py`

**Problem**: Optimize index performance and memory usage
```python
# Input: Index usage patterns
# Output: Optimized index structures
# Requirements: Bloom filters, cache-friendly layouts
```

**Concepts Covered**:
- Bloom filters
- Cache optimization
- Index statistics

**InfluxDB Connection**: Advanced indexing strategies in production databases

---

### Week 2 Integration Lab
**File**: `labs/week2_lab.py`

**Test Scenario**:
- Index 50,000+ time-series points
- Query by various tag combinations
- Test time range queries
- Measure query performance
- Verify index accuracy

**Success Criteria**:
- Sub-millisecond tag lookups
- Efficient time range queries
- Correct query results
- Reasonable memory usage

---

## 📅 Week 3: Query Processing

**Goal**: Build query engine with filtering and aggregation

### Day 15: Basic Filtering
**File**: `exercises/week3_querying/day15_basic_filtering.py`

**Problem**: Implement WHERE clause equivalent
```python
# Input: Filter conditions (tag=value, field>number, etc.)
# Output: Filtered result set
# Requirements: Support AND, OR, comparison operators
```

**Concepts Covered**:
- Boolean logic evaluation
- Predicate pushdown
- Filter optimization

**InfluxDB Connection**: Flux filtering operations

---

### Day 16: Aggregation Functions
**File**: `exercises/week3_querying/day16_aggregations.py`

**Problem**: Implement basic aggregation functions
```python
# Input: Data points and aggregation type
# Output: Aggregated results (sum, count, mean, min, max)
# Requirements: Handle different data types, null values
```

**Concepts Covered**:
- Statistical calculations
- Streaming algorithms
- Numerical stability

**InfluxDB Connection**: Flux aggregation functions

---

### Day 17: Percentile Calculations
**File**: `exercises/week3_querying/day17_percentiles.py`

**Problem**: Calculate percentiles for performance monitoring
```python
# Input: Response time data points
# Output: p50, p95, p99 percentiles
# Requirements: Accurate percentile calculation, memory efficient
```

**Concepts Covered**:
- Quantile algorithms
- Approximate vs exact methods
- Memory-time trade-offs

**InfluxDB Connection**: Percentile functions in monitoring

**Mini Checkpoint**: Calculate percentiles on 10K response time samples

---

### Day 18: Time Window Operations
**File**: `exercises/week3_querying/day18_time_windows.py`

**Problem**: Group data by time intervals
```python
# Input: Time series data and window size (5m, 1h, etc.)
# Output: Aggregated results per time window
# Requirements: Configurable window sizes, alignment
```

**Concepts Covered**:
- Time window algorithms
- Data alignment
- Boundary handling

**InfluxDB Connection**: aggregateWindow in Flux

---

### Day 19: Group By Operations
**File**: `exercises/week3_querying/day19_groupby.py`

**Problem**: Group results by tag values
```python
# Input: Data points and grouping tags
# Output: Results grouped by unique tag combinations
# Requirements: Efficient grouping, memory management
```

**Concepts Covered**:
- Hash-based grouping
- Memory-efficient algorithms
- Result organization

**InfluxDB Connection**: GROUP BY in InfluxQL and Flux

---

### Day 20: Query Optimization
**File**: `exercises/week3_querying/day20_optimization.py`

**Problem**: Optimize query execution plans
```python
# Input: Query with multiple operations
# Output: Optimized execution plan
# Requirements: Filter pushdown, operation reordering
```

**Concepts Covered**:
- Query optimization techniques
- Cost-based decisions
- Execution planning

**Mini Checkpoint**: Optimize complex multi-stage queries

---

### Day 21: Advanced Aggregations
**File**: `exercises/week3_querying/day21_advanced_agg.py`

**Problem**: Implement rate calculations and derivatives
```python
# Input: Counter metrics over time
# Output: Rate of change, derivatives
# Requirements: Handle counter resets, time normalization
```

**Concepts Covered**:
- Rate calculations
- Counter handling
- Time-based derivatives

**InfluxDB Connection**: Rate and derivative functions in Flux

---

### Week 3 Integration Lab
**File**: `labs/week3_lab.py`

**Test Scenario**:
- Complex queries with multiple filters
- Aggregations over large datasets
- Time window operations
- Performance monitoring queries
- Query optimization verification

**Success Criteria**:
- Correct aggregation results
- Efficient time window processing
- Optimized query execution
- Reasonable memory usage

---

## 📅 Week 4: API Layer

**Goal**: Build TCP server with query interface

### Day 22: TCP Server Foundation
**File**: `exercises/week4_api/day22_tcp_server.py`

**Problem**: Implement basic TCP server
```python
# Input: Network connections
# Output: Handle multiple clients, basic protocol
# Requirements: Concurrent connections, error handling
```

**Concepts Covered**:
- Socket programming
- Concurrent connection handling
- Network protocols

**InfluxDB Connection**: InfluxDB's HTTP vs TCP trade-offs

---

### Day 23: Protocol Design
**File**: `exercises/week4_api/day23_protocol.py`

**Problem**: Design simple text-based query protocol
```python
# Input: Query commands over TCP
# Output: Structured responses
# Requirements: Human readable, extensible
```

**Concepts Covered**:
- Protocol design principles
- Command parsing
- Response formatting

**InfluxDB Connection**: InfluxDB's HTTP API design

---

### Day 24: Query Parser
**File**: `exercises/week4_api/day24_query_parser.py`

**Problem**: Parse SQL-like query language
```python
# Input: "SELECT mean(response_time) FROM http WHERE endpoint='/api' AND time > '2025-01-01'"
# Output: Parsed query object
# Requirements: Support SELECT, FROM, WHERE, GROUP BY
```

**Concepts Covered**:
- Lexical analysis
- Recursive descent parsing
- Abstract syntax trees

**InfluxDB Connection**: InfluxQL vs Flux design decisions

**Mini Checkpoint**: Parse and execute complex queries

---

### Day 25: Query Execution Engine
**File**: `exercises/week4_api/day25_execution_engine.py`

**Problem**: Execute parsed queries using previous components
```python
# Input: Parsed query object
# Output: Query results
# Requirements: Integrate storage, indexing, query processing
```

**Concepts Covered**:
- Query execution pipeline
- Component integration
- Error propagation

**InfluxDB Connection**: Query execution in InfluxDB

---

### Day 26: Client Interface
**File**: `exercises/week4_api/day26_client.py`

**Problem**: Build client library for your database
```python
# Input: High-level operations (write, query)
# Output: Network communication handling
# Requirements: Connection management, result formatting
```

**Concepts Covered**:
- Client library design
- Connection pooling
- Result handling

**InfluxDB Connection**: InfluxDB client libraries

---

### Day 27: Error Handling & Validation
**File**: `exercises/week4_api/day27_error_handling.py`

**Problem**: Robust error handling throughout the system
```python
# Input: Various error conditions
# Output: Appropriate error responses and recovery
# Requirements: User-friendly errors, system stability
```

**Concepts Covered**:
- Error handling strategies
- Input validation
- System resilience

**Mini Checkpoint**: Test error conditions and recovery

---

### Day 28: Performance Monitoring
**File**: `exercises/week4_api/day28_monitoring.py`

**Problem**: Add basic performance metrics to your database
```python
# Input: Database operations
# Output: Performance metrics (query time, throughput)
# Requirements: Low overhead, useful insights
```

**Concepts Covered**:
- Performance instrumentation
- Metrics collection
- Monitoring design

**InfluxDB Connection**: How databases monitor themselves

---

### Week 4 Integration Lab
**File**: `labs/week4_lab.py`

**Test Scenario**:
- Full system test via TCP client
- Multiple concurrent connections
- Complex query workload
- Error condition handling
- Performance measurement

**Success Criteria**:
- Complete end-to-end functionality
- Stable under concurrent load
- Correct query results
- Reasonable performance
- Proper error handling

---

## 📅 Week 5: Comparison & Analysis

**Goal**: Compare your implementation with InfluxDB

### Day 29: Performance Benchmarking Setup
**File**: `exercises/week5_comparison/day29_benchmark_setup.py`

**Problem**: Create fair benchmarking framework
```python
# Input: Benchmarking requirements
# Output: Test harness for both databases
# Requirements: Identical workloads, meaningful metrics
```

**Concepts Covered**:
- Benchmarking methodology
- Test harness design
- Performance metrics

**InfluxDB Connection**: InfluxDB benchmarking tools

---

### Day 30: Write Performance Comparison
**File**: `exercises/week5_comparison/day30_write_benchmark.py`

**Problem**: Compare write throughput and latency
```python
# Input: Same dataset written to both databases
# Output: Performance comparison report
# Requirements: Various batch sizes, concurrent writes
```

**Concepts Covered**:
- Write performance factors
- Batch size optimization
- Concurrency impact

**InfluxDB Connection**: InfluxDB write performance characteristics

---

### Day 31: Query Performance Analysis
**File**: `exercises/week5_comparison/day31_query_benchmark.py`

**Problem**: Compare query performance across different scenarios
```python
# Input: Various query patterns
# Output: Performance analysis
# Requirements: Simple queries, aggregations, time ranges
```

**Concepts Covered**:
- Query performance factors
- Index effectiveness
- Optimization opportunities

**InfluxDB Connection**: InfluxDB query optimization

---

### Day 32: Architecture Deep Dive
**File**: `exercises/week5_comparison/day32_architecture_analysis.py`

**Problem**: Analyze architectural differences and trade-offs
```python
# Input: Implementation details from both systems
# Output: Comparative analysis document
# Requirements: Storage, indexing, query processing comparison
```

**Concepts Covered**:
- Architecture comparison
- Trade-off analysis
- Design decision impact

**InfluxDB Connection**: Understanding production database decisions

---

### Week 5 Integration Lab
**File**: `labs/week5_lab.py`

**Test Scenario**:
- Side-by-side performance testing
- Feature completeness comparison
- Scalability analysis
- Resource usage comparison

**Success Criteria**:
- Comprehensive performance data
- Clear understanding of trade-offs
- Identification of optimization opportunities
- Documentation of findings

---

## 📅 Week 6: Production Application

**Goal**: Apply learnings to real-world scenarios

### Day 33: Bottleneck Identification
**File**: `exercises/week6_production/day33_bottleneck_analysis.py`

**Problem**: Identify performance bottlenecks in your implementation
```python
# Input: Performance profiling data
# Output: Bottleneck analysis and improvement plan
# Requirements: Profiling, hotspot identification
```

**Concepts Covered**:
- Performance profiling
- Bottleneck analysis
- Optimization prioritization

**InfluxDB Connection**: Production database optimization

---

### Day 34: Production Optimization
**File**: `exercises/week6_production/day34_optimization.py`

**Problem**: Implement key optimizations identified
```python
# Input: Bottleneck analysis results
# Output: Optimized implementation
# Requirements: Measureable improvements, maintain correctness
```

**Concepts Covered**:
- Performance optimization techniques
- Measurement-driven optimization
- Regression testing

**InfluxDB Connection**: How production databases evolve

---

### Day 35: Real-World Application
**File**: `exercises/week6_production/day35_work_application.py`

**Problem**: Apply learnings to optimize systems at work
```python
# Input: Current work database/system challenges
# Output: Optimization recommendations and implementation
# Requirements: Practical applications, measurable impact
```

**Concepts Covered**:
- Applying database knowledge
- System optimization
- Performance tuning

**InfluxDB Connection**: Optimizing InfluxDB in production

---

### Day 36: Knowledge Documentation
**File**: `exercises/week6_production/day36_documentation.py`

**Problem**: Create comprehensive documentation of learnings
```python
# Input: 6 weeks of learning and implementation
# Output: Technical blog post, documentation, presentation
# Requirements: Clear explanations, practical insights
```

**Concepts Covered**:
- Technical writing
- Knowledge sharing
- Documentation best practices

**InfluxDB Connection**: Sharing database expertise

---

### Week 6 Final Lab
**File**: `labs/week6_lab.py`

**Final Demonstration**:
- Complete system demonstration
- Performance comparison presentation
- Optimization results
- Real-world application examples
- Knowledge sharing preparation

**Success Criteria**:
- Working time-series database
- Clear understanding of database internals
- Practical optimization experience
- Shareable insights and documentation
- Improved performance in work systems

---

## 📊 Assessment Criteria

### Technical Mastery
- [ ] Can explain storage engine trade-offs
- [ ] Understands indexing strategies and their impact
- [ ] Can optimize query performance
- [ ] Knows when to use different aggregation approaches

### Practical Application
- [ ] Successfully optimized real work systems
- [ ] Can benchmark and compare database solutions
- [ ] Has documented reusable insights
- [ ] Can teach concepts to others

### System Thinking
- [ ] Understands end-to-end data flow
- [ ] Can identify system bottlenecks
- [ ] Knows optimization priorities
- [ ] Can make informed architectural decisions

---

## 🎯 Next Steps After Completion

**Immediate Applications**:
- Apply optimizations to work databases
- Share insights with team
- Contribute to database discussions with expertise

**Further Learning**:
- Read "Database Internals" book with deeper understanding
- Explore distributed database concepts
- Study advanced compression algorithms
- Investigate modern storage engines (RocksDB, etc.)

**Career Development**:
- Add unique project to portfolio
- Use experience in interviews
- Become team's database optimization expert
- Consider database-focused career opportunities

---

**Remember**: The goal is deep understanding, not just completing exercises. Take time to understand why things work the way they do.

Good luck with your 6-week database learning journey! 🚀