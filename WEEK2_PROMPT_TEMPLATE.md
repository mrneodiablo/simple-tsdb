# Week 2 Prompt Template

## 🎯 Quick Copy Prompt for Week 2

```
Hi! Tôi đã hoàn thành Week 1 của simple-timeseries-db learning project và muốn tạo Week 2: Indexing & Retrieval.

CONTEXT từ Week 1:
- Đã implement 7 exercises: file operations, serialization, line protocol, partitioning, write ops, storage manager, compression
- Project structure: simple-timeseries-db/ với exercises/, labs/, src/, docs/
- Learning style: <100 LOC per exercise, leetcode-style problems, sequential building
- Approach: Build từ scratch để hiểu concepts, không focus performance

FEEDBACK từ Week 1 implementation:
[Bạn điền feedback về:]
- Code style preference của bạn (OOP vs functional, error handling approach)
- Exercises nào bạn thấy quá dễ/khó
- Areas bạn muốn more/less detail
- Algorithms/concepts bạn muốn explore deeper

WEEK 2 REQUIREMENTS:
Tạo 7 exercises cho Indexing & Retrieval:
1. Hash-based tag indexing (O(1) lookups)
2. Time range indexing (binary search)
3. Series key management
4. Index persistence (save/load from disk)
5. Read operations using indexes
6. Range queries optimization
7. Index maintenance and optimization

Plus 1 integration lab testing full indexing system.

CURRICULUM STRUCTURE đã established:
- Each exercise: problem statement, implementation skeleton, test cases, theory explanation
- Progressive difficulty building on previous exercises
- Real-world connections to InfluxDB architecture
- Integration lab at end of week

Bạn có thể tạo complete Week 2 với 7 exercises + 1 lab không?
```

## 📝 Feedback Template (Fill After Week 1)

### Technical Preferences:
```
CODE STYLE tôi prefer:
- [ ] OOP classes vs [ ] functional approach
- Error handling: [ ] exceptions vs [ ] return codes vs [ ] mixed
- Data structures: [ ] lists [ ] sets [ ] dicts [ ] custom classes
- Documentation: [ ] detailed docstrings [ ] inline comments [ ] minimal

DIFFICULTY LEVEL:
- Week 1 exercises were: [ ] too easy [ ] perfect [ ] too challenging
- I want Week 2 to be: [ ] same level [ ] slightly harder [ ] more detailed
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
Tạo Week 2 (Indexing & Retrieval) cho simple-timeseries-db learning project.

Requirements:
- 7 exercises + 1 integration lab
- Focus: hash indexes, time indexes, series management, persistence
- Style: <100 LOC, leetcode-style, sequential building
- Include: problem statement, skeleton code, tests, theory
- Connect to InfluxDB architecture

Project context: Week 1 covered storage foundation. Week 2 builds indexing system for fast queries.

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
├── labs/week1_lab.py (integration test)
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
- ✅ Basic compression algorithms

### Week 2 Goals:
- Build indexing system for fast queries
- Implement hash-based tag lookups
- Create time range indexing with binary search
- Design series key management
- Enable efficient read operations
- Optimize range queries
- Handle index persistence and maintenance

## 💡 Usage Instructions

1. **Complete Week 1** exercises first
2. **Fill feedback template** based on implementation experience
3. **Copy main prompt** and paste feedback section
4. **Start new Claude session** and paste complete prompt
5. **Get Week 2 exercises** tailored to your learning style

## 🎯 Success Metrics

Week 2 should deliver:
- [ ] 7 progressive exercises building indexing system
- [ ] Each exercise <100 LOC with comprehensive tests
- [ ] Integration lab testing full indexing functionality
- [ ] Clear connections to InfluxDB architecture
- [ ] Difficulty level appropriate to your feedback
- [ ] Code style matching your preferences

---

**File Location**: `/Users/dongvothanh/Data/learning/influxdb_course/simple-timeseries-db/WEEK2_PROMPT_TEMPLATE.md`

**Last Updated**: November 2025
**Usage**: Copy prompt sections as needed for Week 2 creation