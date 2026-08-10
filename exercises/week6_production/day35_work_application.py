#!/usr/bin/env python3
"""
Day 35: Real-World Application (map learnings -> prioritized actions)
====================================================================

Problem: The point of building a TSDB from scratch was to become better at the real
databases you run at work. Turn insight into action: for each challenge in a work
system, name the concept from this course that applies and a concrete recommendation,
then PRIORITIZE — you can't do everything, so rank by impact/effort and surface the
quick wins. This is the bridge from "I learned it" to "I shipped it".

Learning Objectives:
- Model a recommendation: challenge -> learning -> concrete action
- Score impact and effort (1..5) and derive a priority = impact / effort
- Rank recommendations and identify "quick wins" (high impact, low effort)
- Filter to what's actionable now vs later
- Keep the plan as inspectable data (feeds the Day 36 report)

Real-World Connection:
This is a lightweight RICE/ICE prioritization — the framework PMs and staff engineers
use to decide what to build. Applied to InfluxDB in production, it's how you'd choose
between "raise the batch size" (cheap, big) and "re-shard by tenant" (expensive, big).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass
class Recommendation:
    """A single applied learning, scored for prioritization."""
    challenge: str      # the work-system problem
    learning: str       # which course concept applies (e.g. "batching amortizes overhead")
    action: str         # the concrete change to make
    impact: int         # 1..5 (business/perf value)
    effort: int         # 1..5 (cost to implement)

    @property
    def priority(self) -> float:
        """impact / effort (higher = do sooner). effort must be >= 1."""
        # TODO: return impact / effort
        raise NotImplementedError

    @property
    def is_quick_win(self) -> bool:
        """High impact, low effort: impact >= 4 and effort <= 2."""
        # TODO
        raise NotImplementedError


class ApplicationPlan:
    """Collects recommendations and prioritizes them."""

    def __init__(self):
        self._recs: List[Recommendation] = []

    def add(self, rec: Recommendation) -> None:
        """Add a recommendation to the plan."""
        # TODO
        raise NotImplementedError

    def prioritized(self) -> List[Recommendation]:
        """
        Return recommendations sorted by priority DESCENDING. Ties broken by higher
        impact first, then by challenge name (ascending) for determinism.
        """
        # TODO: sort by (-priority, -impact, challenge)
        raise NotImplementedError

    def quick_wins(self) -> List[Recommendation]:
        """Prioritized recommendations that are quick wins (impact>=4, effort<=2)."""
        # TODO: filter prioritized() by is_quick_win
        raise NotImplementedError

    def top(self, n: int) -> List[Recommendation]:
        """The n highest-priority recommendations."""
        # TODO: return prioritized()[:n]
        raise NotImplementedError


def _rec(challenge, learning, action, impact, effort) -> Recommendation:
    return Recommendation(challenge, learning, action, impact, effort)


def test_work_application():
    print("Testing Real-World Application...")

    plan = ApplicationPlan()
    plan.add(_rec("Slow InfluxDB writes", "batching amortizes per-op overhead",
                  "increase client batch size to 5000", impact=5, effort=1))
    plan.add(_rec("High series cardinality", "cardinality drives index memory",
                  "drop unbounded request_id tag", impact=5, effort=2))
    plan.add(_rec("Dashboard p99 spikes", "tail latency needs percentiles",
                  "add p99 panels + aggregateWindow downsampling", impact=3, effort=2))
    plan.add(_rec("Storage cost", "columnar compression saves space",
                  "enable/verify TSM compression settings", impact=2, effort=4))

    # Test 1: add populated the plan
    assert len(plan.prioritized()) == 4
    print("✓ Test 1 passed: add")

    # Test 2: priority math
    r = _rec("x", "l", "a", impact=5, effort=1)
    assert r.priority == 5.0
    assert _rec("y", "l", "a", 2, 4).priority == 0.5
    print("✓ Test 2 passed: priority = impact/effort")

    # Test 3: prioritized order (5/1=5, 5/2=2.5, 3/2=1.5, 2/4=0.5)
    order = [r.challenge for r in plan.prioritized()]
    assert order == ["Slow InfluxDB writes", "High series cardinality",
                     "Dashboard p99 spikes", "Storage cost"]
    print("✓ Test 3 passed: prioritized order")

    # Test 4: quick wins (impact>=4 and effort<=2)
    qw = [r.challenge for r in plan.quick_wins()]
    assert qw == ["Slow InfluxDB writes", "High series cardinality"]
    print("✓ Test 4 passed: quick wins")

    # Test 5: is_quick_win boundaries
    assert _rec("a", "", "", 4, 2).is_quick_win is True
    assert _rec("a", "", "", 4, 3).is_quick_win is False   # too much effort
    assert _rec("a", "", "", 3, 1).is_quick_win is False   # not enough impact
    print("✓ Test 5 passed: quick-win boundaries")

    # Test 6: top(n)
    top2 = [r.challenge for r in plan.top(2)]
    assert top2 == ["Slow InfluxDB writes", "High series cardinality"]
    print("✓ Test 6 passed: top(n)")

    # Test 7: tie-break by impact then name
    p2 = ApplicationPlan()
    p2.add(_rec("Zeta", "", "", 4, 2))   # priority 2.0, impact 4
    p2.add(_rec("Alpha", "", "", 2, 1))  # priority 2.0, impact 2
    p2.add(_rec("Beta", "", "", 4, 2))   # priority 2.0, impact 4
    # same priority 2.0: impact 4 before impact 2; among impact-4, name asc: Beta, Zeta
    assert [r.challenge for r in p2.prioritized()] == ["Beta", "Zeta", "Alpha"]
    print("✓ Test 7 passed: deterministic tie-break")

    # Test 8: empty plan
    assert ApplicationPlan().prioritized() == [] and ApplicationPlan().quick_wins() == []
    print("✓ Test 8 passed: empty plan")

    print("\n🎉 All work application tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement Recommendation.priority/is_quick_win and ApplicationPlan
       (add, prioritized, quick_wins, top).
    2. Run: python day35_work_application.py
    3. All 8 tests should pass.

    Success criteria:
    - priority = impact/effort; quick win = impact>=4 and effort<=2
    - prioritized() sorts by priority desc with deterministic tie-breaks
    - quick_wins() and top(n) filter/slice correctly

    Next steps:
    - Day 36: turn this plan (and your benchmarks) into a shareable report.
    - Think about: why rank by impact/effort rather than impact alone? (A huge win that
      takes a year may lose to three quick wins you ship next week.)
    """
    test_work_application()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. From Learning to Action
   - Knowledge is inert until mapped to a concrete change. The (challenge -> learning ->
     action) triple forces each insight to name the problem it solves and the step to
     take — no vague "we should use indexes".

2. Impact/Effort Prioritization
   - impact/effort (ICE-lite) ranks work by return on investment. It captures the core
     truth of engineering triage: a cheap medium win often beats an expensive big one.

3. Quick Wins
   - High-impact, low-effort items build momentum and credibility. Surfacing them
     explicitly is how you get early value and buy-in for the bigger changes.

4. Plan as Data
   - Keeping recommendations as scored objects (not prose) lets you sort, filter, and
     later render them into a report (Day 36) — the same "data not code/text" theme
     running through the whole course.

Connection to InfluxDB:
- Applied to a real InfluxDB deployment, these are the classic levers: batch size,
  cardinality control, downsampling/retention, and compression settings. Prioritizing
  them by impact/effort is exactly how an SRE plans a tuning sprint.

Trade-offs:
- Impact and effort are estimates — garbage in, garbage out. The framework's value is
  making assumptions explicit and comparable, not precise; revisit the scores as you
  learn more (and after you measure, per Day 34).
"""
