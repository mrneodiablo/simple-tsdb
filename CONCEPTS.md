# Time-Series Database Concepts

## 🎯 Overview

This document explains the theoretical foundations behind time-series databases and how they apply to your implementation. Understanding these concepts will help you make informed design decisions and optimize your system.

---

## 📊 What is a Time-Series Database?

A **time-series database** (TSDB) is optimized for storing and querying data points indexed by time. Unlike traditional databases, TSDBs are designed for:

- **High write throughput**: Millions of data points per second
- **Time-based queries**: "Show me CPU usage for the last hour"
- **Efficient compression**: Time-series data has patterns that can be compressed
- **Retention policies**: Automatic data expiration based on age

### Common Use Cases
- **System monitoring**: CPU, memory, disk usage
- **IoT sensors**: Temperature, humidity, pressure
- **Financial data**: Stock prices, trading volumes
- **Application metrics**: Response times, error rates
- **Load testing**: Request latency, throughput

---

## 🏗️ Core Architecture Components

### 1. Storage Layer

**Purpose**: Persist data efficiently on disk

**Key Design Decisions**:
```python
# Time-based partitioning
data/
├── 2025/01/15/cpu_metrics.json    # Today's CPU data
├── 2025/01/15/memory_metrics.json # Today's memory data
└── 2025/01/14/cpu_metrics.json    # Yesterday's CPU data
```

**Why this works**:
- **Time locality**: Recent data accessed together
- **Retention**: Easy to delete old directories
- **Parallel I/O**: Different time ranges in different files

**Trade-offs**:
- ✅ Simple to implement and understand
- ✅ Natural partitioning by time
- ❌ May create many small files
- ❌ Cross-day queries need multiple file reads

**InfluxDB Comparison**:
InfluxDB uses **TSM (Time-Structured Merge Tree)** files:
- Binary format (vs our JSON)
- Columnar storage (vs our row-based)
- Advanced compression (vs our simple approach)

### 2. Data Model

**Core Entities**:

```python
# Data Point Structure
{
    "measurement": "http_request",        # What we're measuring
    "timestamp": 1672531200.123,         # When (Unix timestamp)
    "tags": {                            # Indexed metadata (strings only)
        "endpoint": "/api/users",
        "method": "GET",
        "status": "200"
    },
    "fields": {                          # Actual values (any type)
        "response_time": 150.5,          # milliseconds (float)
        "bytes_sent": 1024,              # bytes (integer)
        "user_agent": "Mozilla/5.0...",  # string
        "cache_hit": true                # boolean
    }
}
```

**Tags vs Fields - Critical Decision**:

| Aspect | Tags | Fields |
|--------|------|--------|
| **Purpose** | Metadata for filtering/grouping | Actual measured values |
| **Indexed** | Yes (fast queries) | No (full scan required) |
| **Data Types** | Strings only | Integer, Float, String, Boolean |
| **Cardinality** | Should be LOW | Can be HIGH |
| **Query Use** | WHERE, GROUP BY | SELECT, aggregations |

**Example - Good Design**:
```python
# ✅ GOOD: Low cardinality tags
measurement="http_request"
tags={"endpoint": "/api/users", "method": "GET"}    # ~100 unique combinations
fields={"response_time": 150.5, "user_id": "abc123"}
```

**Example - Bad Design**:
```python
# ❌ BAD: High cardinality tags
measurement="http_request"
tags={"user_id": "abc123", "session_id": "xyz789"}  # Millions of combinations!
fields={"response_time": 150.5}
```

**Why cardinality matters**:
- Each unique tag combination creates a **series**
- Series are indexed in memory
- High cardinality = high memory usage = slower queries

### 3. Indexing Layer

**Purpose**: Enable fast queries without scanning all data

**Index Types in Your Implementation**:

1. **Tag Index** (Hash-based):
```python
# Structure: tag_key -> tag_value -> list of file locations
tag_index = {
    "endpoint": {
        "/api/users": ["2025/01/15/http_metrics.json", "2025/01/14/http_metrics.json"],
        "/api/orders": ["2025/01/15/http_metrics.json"]
    },
    "method": {
        "GET": ["2025/01/15/http_metrics.json", "2025/01/14/http_metrics.json"],
        "POST": ["2025/01/15/http_metrics.json"]
    }
}
```

2. **Time Index** (Binary search):
```python
# Structure: file_path -> (min_timestamp, max_timestamp)
time_index = {
    "2025/01/15/http_metrics.json": (1672531200, 1672617599),
    "2025/01/14/http_metrics.json": (1672444800, 1672531199)
}
```

**Query Execution Example**:
```sql
-- Query: "SELECT response_time FROM http_request WHERE endpoint='/api/users' AND time > '2025-01-15'"

-- Step 1: Use tag index to find relevant files
files_with_endpoint = tag_index["endpoint"]["/api/users"]
# Result: ["2025/01/15/http_metrics.json", "2025/01/14/http_metrics.json"]

-- Step 2: Use time index to filter by time
files_in_timerange = []
for file in files_with_endpoint:
    if time_index[file].max_time >= query_start_time:
        files_in_timerange.append(file)
# Result: ["2025/01/15/http_metrics.json"]

-- Step 3: Scan only relevant files
scan_files(files_in_timerange, filters=["endpoint=/api/users"])
```

### 4. Query Processing

**Query Pipeline**:

1. **Parse** query string into structured format
2. **Plan** execution using available indexes
3. **Filter** data using indexes and predicates
4. **Aggregate** results (sum, mean, percentiles, etc.)
5. **Format** output for client

**Aggregation Functions**:

```python
# Statistical aggregations
mean(values)     # Average value
sum(values)      # Total sum
count(values)    # Number of points
min(values)      # Minimum value
max(values)      # Maximum value

# Percentiles (critical for performance monitoring)
percentile(values, 0.50)  # p50 (median)
percentile(values, 0.95)  # p95 (95th percentile)
percentile(values, 0.99)  # p99 (99th percentile)

# Time-based aggregations
window_mean(values, window_size="5m")  # 5-minute averages
rate(counter_values, time_unit="1s")   # Rate per second
```

**Why percentiles matter**:
- **Average** can be misleading (outliers skew results)
- **p95** = "95% of requests were faster than this"
- **p99** = "99% of requests were faster than this"
- Essential for SLA monitoring and performance analysis

---

## 💾 Storage Engine Deep Dive

### Append-Only Architecture

**Why append-only**:
- Time-series data is naturally chronological
- No updates to historical data (immutable)
- Optimizes for write performance
- Simplifies concurrency control

**Write Path**:
```
Data Point → Serialize → Append to File → Update Indexes
```

**Read Path**:
```
Query → Index Lookup → File Scan → Filter → Aggregate → Result
```

### Compression Strategies

**Time-series data has patterns**:

1. **Delta Encoding** (timestamps):
```python
# Original timestamps
[1672531200, 1672531201, 1672531202, 1672531203]

# Delta encoded (store differences)
[1672531200, +1, +1, +1]  # Much smaller!
```

2. **Run-Length Encoding** (repeated values):
```python
# Original
[100, 100, 100, 100, 200, 200, 300]

# Run-length encoded
[(100, 4), (200, 2), (300, 1)]  # Smaller for repetitive data
```

3. **Gorilla Compression** (floating point):
- XOR consecutive values
- Store only the differing bits
- Achieves 90%+ compression on typical metrics

### File Organization

**Single File Approach** (your implementation):
```
cpu_metrics_2025_01_15.json:
[
  {"timestamp": 1672531200, "tags": {...}, "fields": {...}},
  {"timestamp": 1672531201, "tags": {...}, "fields": {...}},
  ...
]
```

**Pros**: Simple, human-readable, easy debugging
**Cons**: Inefficient for large datasets, no compression

**LSM Tree Approach** (production databases):
```
Level 0: [newest_data.sst] (in memory)
Level 1: [recent_1.sst, recent_2.sst]
Level 2: [older_1.sst, older_2.sst, older_3.sst, older_4.sst]
```

**Pros**: Excellent write performance, good compression, handles large datasets
**Cons**: Complex to implement, read amplification, compaction overhead

---

## 🔍 Query Optimization Techniques

### 1. Predicate Pushdown

**Concept**: Move filters as close to data as possible

```python
# Inefficient: Read all data then filter
all_data = read_all_files()
filtered = [point for point in all_data if point.endpoint == "/api/users"]

# Efficient: Filter during file reading
filtered = []
for file in relevant_files:
    for point in read_file(file):
        if point.endpoint == "/api/users":  # Filter immediately
            filtered.append(point)
```

### 2. Index Utilization

**Query Planning**:
```python
def plan_query(query):
    # 1. Use tag indexes to identify relevant files
    files = find_files_with_tags(query.tag_filters)

    # 2. Use time index to narrow by time range
    files = filter_files_by_time(files, query.time_range)

    # 3. Estimate cost and choose best approach
    if len(files) < 10:
        return scan_files(files)
    else:
        return use_specialized_index(query)
```

### 3. Aggregation Optimization

**Streaming Aggregation**:
```python
# Memory-efficient: Process one point at a time
def streaming_mean(data_stream):
    count = 0
    sum_value = 0
    for point in data_stream:
        count += 1
        sum_value += point.value
    return sum_value / count

# Memory-inefficient: Load all data first
def batch_mean(data_stream):
    all_points = list(data_stream)  # Loads everything into memory!
    return sum(p.value for p in all_points) / len(all_points)
```

---

## 📈 Performance Characteristics

### Write Performance

**Factors affecting write speed**:

1. **Batch Size**: Larger batches amortize I/O overhead
2. **File System**: SSD vs HDD, file system type
3. **Serialization**: Binary vs JSON vs text
4. **Indexing Overhead**: More indexes = slower writes
5. **Compression**: CPU time vs storage space trade-off

**Typical Performance** (single node):
- **Your JSON implementation**: ~10K points/second
- **Production TSDB**: ~1M points/second
- **Difference**: Binary format, advanced compression, optimized I/O

### Query Performance

**Time Complexity**:

| Operation | Without Index | With Index | Your Implementation |
|-----------|---------------|------------|-------------------|
| Tag Filter | O(n) | O(1) | O(k) where k=files |
| Time Range | O(n) | O(log n) | O(k) where k=files |
| Aggregation | O(n) | O(m) | O(m) where m=matches |

**Real-World Query Times**:
- **Simple tag filter**: < 1ms (with good indexes)
- **Complex aggregation**: 10-100ms (depending on data volume)
- **Large time range**: 100ms-1s (depends on compression)

### Memory Usage

**Your Implementation**:
- **Tag Index**: ~1MB per million unique tag combinations
- **Time Index**: ~1KB per file
- **Query Buffer**: Depends on result set size

**Production TSDB**:
- **Series Cache**: ~1GB for 10M active series
- **Block Cache**: ~2-4GB for frequently accessed data
- **Bloom Filters**: ~10MB for 100M time series

---

## 🔄 Comparison with Production Systems

### InfluxDB Architecture

**Storage Engine (TSM)**:
- **File Format**: Binary, columnar storage
- **Compression**: Snappy + specialized time-series compression
- **Indexing**: TSI (Time Series Index) with bloom filters
- **Write Path**: WAL → Cache → TSM files
- **Read Path**: Index lookup → TSM file scan → decompress

**vs Your Implementation**:
| Feature | Your DB | InfluxDB |
|---------|---------|----------|
| Storage | JSON files | Binary TSM |
| Compression | None | Advanced |
| Index | Hash table | TSI + Bloom |
| Query Language | Simple SQL | Flux |
| Write Performance | 10K/sec | 1M+/sec |
| Production Ready | No | Yes |

### Other TSDBs

**Prometheus**:
- **Focus**: Metrics collection and alerting
- **Storage**: Custom binary format with LevelDB
- **Query**: PromQL (functional language)
- **Architecture**: Pull-based (scraping)

**TimescaleDB**:
- **Base**: PostgreSQL extension
- **Storage**: Hypertables (partitioned tables)
- **Query**: Standard SQL
- **Features**: Full ACID compliance, joins

**ClickHouse**:
- **Focus**: Real-time analytics
- **Storage**: Columnar with advanced compression
- **Query**: SQL with array functions
- **Performance**: Extremely fast aggregations

---

## 🎓 Learning Progression

### Week 1-4: Foundation Building

**What you're learning**:
1. **File I/O and serialization**: How data gets to/from disk
2. **Indexing strategies**: How to make queries fast
3. **Query processing**: How to filter and aggregate data
4. **API design**: How to expose functionality to users

**Why it's valuable**:
- Understand performance trade-offs
- Debug issues in production systems
- Make informed technology choices
- Optimize existing databases

### Week 5-6: Real-World Application

**Comparative analysis**:
- Benchmark your implementation vs InfluxDB
- Understand why production systems are complex
- Identify optimization opportunities
- Apply learnings to work projects

---

## 💡 Key Insights for Your Career

### Database Optimization

**Common Performance Issues**:
1. **High Cardinality**: Too many unique tag combinations
2. **Inefficient Queries**: Scanning when indexes could be used
3. **Write Hotspots**: All writes going to same partition
4. **Memory Pressure**: Indexes growing too large

**Optimization Strategies**:
1. **Schema Design**: Choose tags vs fields carefully
2. **Query Patterns**: Understand your workload
3. **Resource Planning**: Size memory and storage appropriately
4. **Monitoring**: Track key metrics continuously

### System Design Thinking

**Questions to ask**:
- What are the read/write patterns?
- How much data needs to be retained?
- What are the consistency requirements?
- How will the system scale?
- What are the failure modes?

### Interview Preparation

**Topics you can discuss**:
- Time-series database internals
- Storage engine trade-offs
- Query optimization techniques
- Indexing strategies
- Performance tuning approaches

---

This foundation will serve you well as you progress through the exercises and apply these concepts in real-world scenarios. Remember: the goal is understanding, not just implementation!