#!/usr/bin/env python3
"""
Day 32: Architecture Deep Dive (trade-off matrix & recommender)
==============================================================

Problem: Benchmarks give numbers; engineering maturity is knowing what the numbers
MEAN and when a design is the right choice. Step back from microseconds and compare
architectures along the dimensions that matter — write throughput, query flexibility,
operational simplicity, compression, cardinality handling — then turn "it depends" into
a defensible recommendation for a given workload.

Learning Objectives:
- Model an architecture as scores across comparison dimensions
- Encode a workload as weights (which dimensions this use case cares about)
- Compute a weighted score and RECOMMEND the best-fit architecture
- Build a readable trade-off matrix
- Reason honestly: your simple TSDB wins on some axes, InfluxDB on others

Real-World Connection:
This is the analysis every architecture decision record (ADR) contains: not "X is
best" but "X for workload A, Y for workload B, here's why". InfluxDB's TSM+TSI is tuned
for high write throughput and cardinality; a simple JSON store wins on simplicity and
debuggability. Both are correct — for different jobs.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# The dimensions we score every architecture on (higher = better), scale 1..5.
DIMENSIONS = [
    "write_throughput",
    "query_flexibility",
    "operational_simplicity",
    "compression",
    "cardinality_handling",
]


@dataclass
class Architecture:
    """An architecture profiled by 1..5 scores across DIMENSIONS."""
    name: str
    dimensions: Dict[str, int]
    notes: str = ""

    def score_for(self, dim: str) -> int:
        return self.dimensions.get(dim, 0)


# Reference profiles (given data — these are the "facts" you're reasoning about).
INFLUXDB = Architecture(
    name="InfluxDB (TSM + TSI)",
    dimensions={
        "write_throughput": 5,       # LSM-style TSM, batched, columnar
        "query_flexibility": 4,      # Flux/InfluxQL, rich functions
        "operational_simplicity": 2, # tuning, cardinality limits, compaction to manage
        "compression": 5,            # Gorilla/delta/RLE columnar compression
        "cardinality_handling": 4,   # TSI built for high series cardinality
    },
    notes="Production TSDB: columnar TSM storage + inverted TSI index.",
)

SIMPLE_TSDB = Architecture(
    name="simple-timeseries-db (this project)",
    dimensions={
        "write_throughput": 2,       # JSON files, no columnar batching
        "query_flexibility": 3,      # your Week 3/4 engine: filter/agg/group/window
        "operational_simplicity": 5, # plain files + dicts; trivial to inspect/debug
        "compression": 2,            # basic delta/RLE only
        "cardinality_handling": 2,   # in-memory dict indexes, no cardinality controls
    },
    notes="Learning TSDB: JSON storage + hash/time indexes + in-memory query engine.",
)


@dataclass
class Workload:
    """A use case as per-dimension importance weights (need not sum to 1)."""
    name: str
    weights: Dict[str, float] = field(default_factory=dict)


class ArchitectureComparison:
    """Scores architectures against workloads and recommends the best fit."""

    def __init__(self):
        self._archs: List[Architecture] = []

    def register(self, arch: Architecture) -> None:
        """Add an architecture to the comparison set."""
        # TODO: append arch to self._archs
        self._archs.append(arch)

    def score(self, arch: Architecture, workload: Workload) -> float:
        """
        Weighted score = sum over dimensions of (arch.score_for(dim) * weight),
        for each dim present in workload.weights.
        """
        # TODO: sum arch.score_for(dim) * w for dim, w in workload.weights.items()
        return sum(arch.score_for(dim) * w for dim, w in workload.weights.items())

    def recommend(self, workload: Workload) -> Architecture:
        """
        Return the registered architecture with the highest weighted score for the
        workload. Raise ValueError if no architectures are registered. On a tie, return
        the first-registered among the top scorers.
        """
        # TODO: argmax over self._archs by self.score(arch, workload); ValueError if empty.
        if not self._archs:
            raise ValueError("No architectures registered for comparison.")
        best_arch = max(self._archs, key=lambda arch: self.score(arch, workload))
        return best_arch

    def ranking(self, workload: Workload) -> List[tuple]:
        """Return [(arch, score), ...] sorted by score descending (stable)."""
        # TODO: build and sort the (arch, score) pairs, highest first.
        return sorted(
            ((arch, self.score(arch, workload)) for arch in self._archs),
            key=lambda pair: pair[1],
            reverse=True,
        )

    def matrix(self) -> Dict[str, Dict[str, int]]:
        """Return {arch_name: {dimension: score}} for all registered architectures."""
        # TODO
        return {arch.name: {dim: arch.score_for(dim) for dim in DIMENSIONS} for arch in self._archs}


# Handy pre-built workloads for the tests / lab.
WRITE_HEAVY = Workload("write-heavy ingestion", {
    "write_throughput": 3.0, "compression": 2.0, "cardinality_handling": 2.0,
    "operational_simplicity": 0.5,
})
LEARNING_DEBUGGABILITY = Workload("learning / debuggability", {
    "operational_simplicity": 3.0, "query_flexibility": 1.0,
})


def test_architecture_analysis():
    print("Testing Architecture Analysis...")

    cmp = ArchitectureComparison()
    cmp.register(INFLUXDB)
    cmp.register(SIMPLE_TSDB)

    # Test 1: register populated the set; matrix reflects both
    m = cmp.matrix()
    assert set(m.keys()) == {INFLUXDB.name, SIMPLE_TSDB.name}
    assert m[INFLUXDB.name]["write_throughput"] == 5
    print("✓ Test 1 passed: register + matrix")

    # Test 2: weighted score math
    # InfluxDB on WRITE_HEAVY: 5*3 + 5*2 + 4*2 + 2*0.5 = 15+10+8+1 = 34
    s_influx = cmp.score(INFLUXDB, WRITE_HEAVY)
    assert abs(s_influx - 34.0) < 1e-9
    # SIMPLE on WRITE_HEAVY: 2*3 + 2*2 + 2*2 + 5*0.5 = 6+4+4+2.5 = 16.5
    s_simple = cmp.score(SIMPLE_TSDB, WRITE_HEAVY)
    assert abs(s_simple - 16.5) < 1e-9
    print("✓ Test 2 passed: weighted score")

    # Test 3: recommend InfluxDB for a write-heavy workload
    assert cmp.recommend(WRITE_HEAVY).name == INFLUXDB.name
    print("✓ Test 3 passed: recommend write-heavy -> InfluxDB")

    # Test 4: recommend simple TSDB for a learning/debuggability workload
    # SIMPLE: 5*3 + 3*1 = 18 ; INFLUX: 2*3 + 4*1 = 10
    assert cmp.recommend(LEARNING_DEBUGGABILITY).name == SIMPLE_TSDB.name
    print("✓ Test 4 passed: recommend learning -> simple TSDB")

    # Test 5: ranking is sorted descending
    ranking = cmp.ranking(WRITE_HEAVY)
    scores = [s for _, s in ranking]
    assert scores == sorted(scores, reverse=True)
    assert ranking[0][0].name == INFLUXDB.name
    print("✓ Test 5 passed: ranking order")

    # Test 6: empty comparison raises on recommend
    empty = ArchitectureComparison()
    try:
        empty.recommend(WRITE_HEAVY)
        assert False, "expected ValueError"
    except ValueError:
        pass
    print("✓ Test 6 passed: empty recommend raises")

    # Test 7: a dimension absent from an arch scores 0 for that dim
    partial = Architecture("partial", {"write_throughput": 4})
    # workload weighting only compression (which partial lacks) -> score 0
    only_comp = Workload("comp", {"compression": 2.0})
    assert cmp.score(partial, only_comp) == 0.0
    print("✓ Test 7 passed: missing dimension scores 0")

    # Test 8: tie returns the first-registered top scorer
    tie_cmp = ArchitectureComparison()
    a = Architecture("A", {"x": 3})
    b = Architecture("B", {"x": 3})
    tie_cmp.register(a)
    tie_cmp.register(b)
    assert tie_cmp.recommend(Workload("w", {"x": 1.0})).name == "A"
    print("✓ Test 8 passed: tie -> first registered")

    print("\n🎉 All architecture analysis tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement ArchitectureComparison.register/score/recommend/ranking/matrix.
    2. Run: python day32_architecture_analysis.py
    3. All 8 tests should pass.

    Success criteria:
    - score() is a correct weighted sum over the workload's dimensions
    - recommend() picks the max-score architecture (first-registered wins ties)
    - ranking() sorts descending; matrix() reports all scores
    - a workload weighting a missing dimension contributes 0

    Next steps:
    - Run the Week 5 Integration Lab: labs/week5_lab.py (full benchmark suite + report).
    - Think about: what would raise your simple TSDB's write_throughput score? What would
      it cost you on operational_simplicity? (This is the real trade-off.)
    """
    test_architecture_analysis()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Multi-Dimensional Trade-offs
   - No architecture is "best" on every axis. Scoring across dimensions forces you to
     name the axes and admit where each design loses — the honesty that separates
     analysis from advocacy.

2. Workload-Weighted Decisions
   - The right choice depends on what the WORKLOAD values. Encoding a use case as weights
     turns a subjective debate into a reproducible calculation: same weights, same
     recommendation.

3. Reference Profiles as Data
   - Capturing InfluxDB vs your project as scored data (not prose) makes the comparison
     inspectable and updatable — add a dimension, rescore, re-recommend.

4. Recommendation, Not Dogma
   - The recommender output is "for THIS workload, THIS design" — with a ranking and a
     matrix behind it. That's exactly the form of an architecture decision record.

Connection to InfluxDB:
- InfluxDB's TSM (columnar, compressed) + TSI (inverted index) optimize write throughput,
  compression, and cardinality — at the cost of operational complexity (compaction,
  cardinality limits, tuning). Your JSON+dict design inverts that trade-off. Both are
  legitimate points on the design space.

Trade-offs:
- Scoring is inherently subjective (who sets the 1..5 and the weights?). Its value is not
  false precision but STRUCTURE: it makes assumptions explicit and arguable, which is
  what good technical decisions require.
"""
