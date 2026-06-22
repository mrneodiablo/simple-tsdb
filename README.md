# Simple Time-Series Database

## 🎯 Project Overview

A learning project to build a minimal time-series database from scratch in Python3. This project helps you understand database internals by implementing core concepts step by step.

**Learning Goals:**
- Understand time-series database architecture from first principles
- Learn storage engines, indexing, query processing
- Compare your implementation with production databases (InfluxDB)
- Apply learnings to optimize real-world systems

## 🏗️ What You'll Build

A working time-series database with:
- **Storage Layer**: File-based storage with JSON format
- **Index Layer**: Hash-based tag indexing + time range indexing
- **Query Layer**: Filtering, aggregation, time windows
- **API Layer**: TCP server with simple query language
- **Benchmarks**: Performance comparison with InfluxDB

## 📚 6-Week Learning Path

### **Phase 1: Core Implementation (Weeks 1-4)**

**Week 1: Storage Foundation**
- File operations and data structures
- Line protocol parsing
- Time-based partitioning
- Write operations
- *Integration Lab*: Write 1000 data points to storage

**Week 2: Indexing & Retrieval**
- Hash-based tag indexing
- Time range indexing (binary search)
- Series key management
- Read operations
- *Integration Lab*: Query data by tags and time ranges

**Week 3: Query Processing**
- Basic filtering operations
- Aggregation functions (mean, sum, count, percentiles)
- Time window operations
- Simple query optimization
- *Integration Lab*: Complex multi-dimensional queries

**Week 4: API Layer**
- TCP server implementation
- Query language parser
- Error handling and validation
- Client interface
- *Integration Lab*: Full system test via TCP client

### **Phase 2: Real-World Application (Weeks 5-6)**

**Week 5: Comparison & Analysis**
- Performance benchmarking vs InfluxDB
- Architecture comparison (TSM vs your approach)
- Feature analysis and trade-offs
- Bottleneck identification
- *Lab*: Load testing both systems

**Week 6: Production Application**
- Apply learnings to optimize work systems
- Design production-ready improvements
- Create technical documentation
- Knowledge sharing preparation
- *Final Lab*: Present findings and recommendations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Basic understanding of databases and networking
- Completed InfluxDB Module 7 (Architecture Deep Dive)

### Setup
```bash
git clone <your-repo>
cd simple-timeseries-db
pip install -r requirements.txt
```

### Your First Exercise
```bash
cd exercises/week1_storage
python day1_file_operations.py
```

## 📁 Project Structure

```
simple-timeseries-db/
├── README.md                    # This file
├── CURRICULUM.md               # Detailed 6-week curriculum
├── CONCEPTS.md                 # Theory and concepts explanation
├── requirements.txt            # Python dependencies
├── exercises/                  # Daily coding exercises
│   ├── week1_storage/          # 7 exercises + checkpoints
│   ├── week2_indexing/         # 7 exercises + checkpoints
│   ├── week3_querying/         # 7 exercises + checkpoints
│   ├── week4_api/              # 7 exercises + checkpoints
│   ├── week5_comparison/       # 4 exercises + benchmarks
│   └── week6_production/       # 4 exercises + final project
├── labs/                       # Integration labs (weekly)
│   ├── week1_lab.py           # Test storage layer
│   ├── week2_lab.py           # Test indexing layer
│   ├── week3_lab.py           # Test query layer
│   ├── week4_lab.py           # Test full system
│   ├── week5_lab.py           # Performance comparison
│   └── week6_lab.py           # Final system demonstration
├── src/tsdb/                   # Core implementation
│   ├── __init__.py
│   ├── storage/               # Storage engine
│   │   ├── __init__.py
│   │   ├── file_manager.py
│   │   ├── serializer.py
│   │   └── partitioner.py
│   ├── index/                 # Indexing system
│   │   ├── __init__.py
│   │   ├── tag_index.py
│   │   ├── time_index.py
│   │   └── series_manager.py
│   ├── query/                 # Query processing
│   │   ├── __init__.py
│   │   ├── filter.py
│   │   ├── aggregator.py
│   │   └── optimizer.py
│   └── server/                # API layer
│       ├── __init__.py
│       ├── tcp_server.py
│       ├── query_parser.py
│       └── client.py
├── tests/                     # Unit tests (leetcode style)
│   ├── test_storage.py
│   ├── test_index.py
│   ├── test_query.py
│   └── test_server.py
├── benchmarks/                # Performance testing
│   ├── benchmark_write.py
│   ├── benchmark_read.py
│   └── compare_influxdb.py
├── docs/                      # Documentation
│   ├── architecture.md       # System architecture
│   ├── storage_design.md     # Storage layer design
│   ├── indexing_strategy.md  # Indexing approach
│   └── query_processing.md   # Query execution
└── data/                      # Sample datasets
    ├── sample_metrics.json
    ├── load_test_data.json
    └── time_series_patterns.json
```

## 🎯 Learning Philosophy

### Why Build From Scratch?
- **Deep Understanding**: Implement core algorithms yourself
- **Debug Skills**: Learn how systems fail and recover
- **Interview Prep**: Explain database internals from first principles
- **Career Growth**: Unique insights that AI can't provide

### Exercise Design Principles
- **<100 lines per exercise**: Focus on concepts, not complexity
- **Sequential building**: Each exercise builds on previous ones
- **Real-world connection**: Link to InfluxDB and other production DBs
- **Incremental enhancement**: Revisit previous layers with new requirements

### Testing Strategy
- **Unit tests**: Leetcode-style problem validation
- **Integration labs**: End-to-end system verification
- **Benchmarks**: Performance measurement and comparison
- **Mini-checkpoints**: Frequent validation to catch issues early

## 📊 Success Metrics

By the end of 6 weeks, you will have:

**Week 1-4 Milestones:**
- [ ] Working storage engine that persists data to JSON files
- [ ] Tag and time-based indexing for fast queries
- [ ] Query processor with filtering and aggregation
- [ ] TCP server accepting and processing queries

**Week 5-6 Milestones:**
- [ ] Performance comparison showing your DB vs InfluxDB characteristics
- [ ] Technical analysis of architecture trade-offs
- [ ] Applied optimizations to real work systems
- [ ] Comprehensive documentation and knowledge sharing

**Learning Outcomes:**
- [ ] Can explain database storage engines from first principles
- [ ] Understand indexing strategies and their trade-offs
- [ ] Can optimize query performance in production systems
- [ ] Have unique insights to share with your team
- [ ] Prepared for database-focused technical interviews

## 🤝 How to Use This Project

### Daily Routine (30-60 minutes)
1. Read the exercise description and concepts
2. Implement the solution (aim for <100 LOC)
3. Run the unit tests to verify correctness
4. Document your learnings and observations

### Weekly Routine
1. Complete 4-7 daily exercises
2. Run the integration lab to test the full system
3. Review and refactor code if needed
4. Plan the next week's learning

### Learning Tips
- **Don't rush**: Understanding is more important than speed
- **Debug actively**: When things break, investigate why
- **Compare approaches**: Think about alternatives and trade-offs
- **Document insights**: Keep notes for future reference
- **Ask questions**: Why does this approach work? What are the limitations?

## 🔗 Related Resources

**Background Reading:**
- InfluxDB Module 7: Architecture Deep Dive (prerequisite)
- [Database Internals Book](https://databass.dev/)
- [Designing Data-Intensive Applications](https://dataintensive.net/)

**Production References:**
- [InfluxDB TSM Engine](https://docs.influxdata.com/influxdb/v2/reference/internals/storage-engine/)
- [Time Series Database Papers](https://github.com/xephonhq/awesome-time-series-database)

**Implementation Inspiration:**
- [Build Your Own Database](https://build-your-own.org/database/)
- [Let's Build a Simple Database](https://cstack.github.io/db_tutorial/)

## 📞 Support & Discussion

- **Questions**: Document in `docs/questions.md`
- **Issues**: Track in `docs/issues_encountered.md`
- **Learnings**: Share in `docs/insights.md`
- **Team sharing**: Use final documentation in Week 6

---

## 🚦 Next Steps

1. **Read [CURRICULUM.md](CURRICULUM.md)** for detailed daily exercises
2. **Review [CONCEPTS.md](CONCEPTS.md)** for theoretical background
3. **Start with Week 1, Day 1**: `exercises/week1_storage/day1_file_operations.py`
4. **Set up development environment** with `pip install -r requirements.txt`

**Remember**: The goal isn't to build the next InfluxDB. It's to understand how databases work so you can be a better engineer.

Good luck with your learning journey! 🎉

---

**Project Version**: 1.0
**Created**: November 2025
**Learning Time**: 6 weeks (3-4 hours/week)
**Difficulty**: Intermediate (requires basic Python and database concepts)