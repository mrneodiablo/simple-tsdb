#!/usr/bin/env python3
"""
Day 36: Knowledge Documentation (structured report / blog generator)
===================================================================

Problem: The final capstone deliverable isn't code — it's COMMUNICATION. Six weeks of
learning and measurements are worthless to your team if they live only in your head.
Build a small report generator that turns structured findings (sections, metrics,
prioritized actions) into clean Markdown: consistent headers, metric tables, and a
conclusion — the blog post / internal doc that makes your work shareable.

Learning Objectives:
- Assemble a document from structured pieces (title, sections, tables)
- Render a metrics dict as a Markdown table
- Keep output deterministic and assertable (return strings, don't print/write)
- Build a fluent API (methods return self) for readable report construction
- Separate content (data) from rendering (Markdown formatting)

Real-World Connection:
Every good engineering project ends with an artifact: a design doc, a benchmark
write-up, an ADR, a blog post. Tools like MkDocs, Sphinx, and Jupyter-to-Markdown all
turn structured content into shareable docs. Generating Markdown from data keeps reports
consistent and regenerable as numbers change.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Section:
    heading: str
    lines: List[str] = field(default_factory=list)


class ReportBuilder:
    """
    Fluent Markdown report builder. Content is stored structurally and rendered by
    build(); each add_* method returns self so calls can chain.
    """

    def __init__(self, title: str):
        self.title = title
        self._sections: List[Section] = []

    def section(self, heading: str, *lines: str) -> "ReportBuilder":
        """Add a section with a heading and zero or more body lines."""
        # TODO: append a Section(heading, list(lines)); return self
        self._sections.append(Section(heading, list(lines)))
        return self

    def metric_table(self, heading: str, metrics: Dict[str, object]) -> "ReportBuilder":
        """
        Add a section whose body is a Markdown table of the metrics dict:

            | Metric | Value |
            | --- | --- |
            | <k> | <v> |

        Preserve insertion order of `metrics`. Return self.
        """
        # TODO: build the table lines (header, separator, one row per item) and store
        #       them as a Section(heading, lines); return self.
        lines = render_markdown_table(metrics)
        self._sections.append(Section(heading, lines))
        return self

    def bullets(self, heading: str, items: List[str]) -> "ReportBuilder":
        """Add a section rendering `items` as a Markdown bullet list ('- item')."""
        # TODO: prefix each item with "- "; store as a Section; return self
        lines = [f"- {item}" for item in items]
        self._sections.append(Section(heading, lines))
        return self

    def build(self) -> str:
        """
        Render the whole report as Markdown:
            # <title>

            ## <section heading>

            <section lines...>

            ## <next section>
            ...
        Rules: a single "# title" first; each section is "## heading" then a blank line
        then its lines; sections separated by a blank line; no trailing whitespace.
        """
        # TODO: assemble "# title", then each "## heading" + body, joined by blank lines.
        report_lines = [f"# {self.title}", ""]  # H1 title + blank line
        for section in self._sections:
            report_lines.append(f"## {section.heading}")
            report_lines.append("")
            report_lines.extend(section.lines)
            report_lines.append("")
        return "\n".join(report_lines).rstrip()


def render_markdown_table(metrics: Dict[str, object]) -> List[str]:
    """
    Standalone helper: render a metrics dict as Markdown table lines
    (["| Metric | Value |", "| --- | --- |", "| k | v |", ...]).
    An empty dict yields just the header + separator.
    """
    # TODO: return the header row, separator row, and one "| k | v |" row per item.
    lines = ["| Metric | Value |", "| --- | --- |"]
    for k, v in metrics.items():
        lines.append(f"| {k} | {v} |")
    return lines


def test_documentation():
    print("Testing Knowledge Documentation...")

    # Test 1: standalone table helper
    rows = render_markdown_table({"throughput": "160k/s", "p95": "0.5ms"})
    assert rows[0] == "| Metric | Value |"
    assert rows[1] == "| --- | --- |"
    assert rows[2] == "| throughput | 160k/s |"
    assert rows[3] == "| p95 | 0.5ms |"
    print("✓ Test 1 passed: markdown table helper")

    # Test 2: empty dict -> header + separator only
    assert render_markdown_table({}) == ["| Metric | Value |", "| --- | --- |"]
    print("✓ Test 2 passed: empty table")

    # Test 3: title renders as H1
    md = ReportBuilder("TSDB Capstone Report").build()
    assert md.splitlines()[0] == "# TSDB Capstone Report"
    print("✓ Test 3 passed: H1 title")

    # Test 4: section renders as H2 with body
    md = (ReportBuilder("R")
          .section("Overview", "Built a TSDB in 6 weeks.", "It works.")
          .build())
    assert "## Overview" in md
    assert "Built a TSDB in 6 weeks." in md and "It works." in md
    print("✓ Test 4 passed: section H2 + body")

    # Test 5: fluent chaining returns the builder
    rb = ReportBuilder("R")
    assert rb.section("A", "x") is rb and rb.bullets("B", ["one"]) is rb
    print("✓ Test 5 passed: fluent API")

    # Test 6: metric_table embeds a table under a heading
    md = (ReportBuilder("R")
          .metric_table("Results", {"speedup": "8357x", "points": 20000})
          .build())
    assert "## Results" in md
    assert "| speedup | 8357x |" in md and "| points | 20000 |" in md
    print("✓ Test 6 passed: metric table section")

    # Test 7: bullets render as a Markdown list
    md = ReportBuilder("R").bullets("Wins", ["batch size", "drop tag"]).build()
    assert "- batch size" in md and "- drop tag" in md
    print("✓ Test 7 passed: bullet list")

    # Test 8: full report has ordered sections and clean structure
    md = (ReportBuilder("Capstone")
          .section("Intro", "hi")
          .metric_table("Metrics", {"a": 1})
          .bullets("Next", ["ship it"])
          .build())
    # order preserved: Intro before Metrics before Next
    assert md.index("## Intro") < md.index("## Metrics") < md.index("## Next")
    # starts with the H1 and has no trailing whitespace
    assert md.startswith("# Capstone\n")
    assert md == md.rstrip()
    print("✓ Test 8 passed: full report structure")

    print("\n🎉 All documentation tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement render_markdown_table and ReportBuilder
       (section, metric_table, bullets, build).
    2. Run: python day36_documentation.py
    3. All 8 tests should pass.

    Success criteria:
    - Title -> H1, sections -> H2 with bodies, in insertion order
    - metric_table / render_markdown_table produce valid Markdown tables
    - the fluent API chains; build() returns clean Markdown (no trailing whitespace)

    Next steps:
    - Run the Week 6 capstone lab: labs/week6_lab.py (profile -> optimize -> document).
    - Think about: why generate the report from DATA instead of writing prose by hand?
      (Hint: regenerate it whenever the numbers change — no stale copy-paste.)
    """
    test_documentation()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Documentation Is a Deliverable
   - Code that no one understands or can act on has little leverage. A clear write-up
     multiplies the value of the work by making it teachable and reusable.

2. Structured Content -> Rendered Output
   - Storing sections/metrics as data and rendering Markdown at the end separates WHAT
     you say from HOW it's formatted. Change the renderer once (HTML, PDF) without
     touching the content.

3. Regenerable Reports
   - Because the report is built from data (benchmarks, the Day 35 plan), you regenerate
     it whenever numbers change — no stale hand-edited tables. This is why docs-as-code
     wins over copy-pasting results.

4. Fluent APIs
   - Methods returning self let a report read top-to-bottom like an outline. Small
     ergonomic wins like this are what make a tool pleasant enough to actually use.

Connection to InfluxDB / the field:
- Benchmark write-ups, ADRs, and runbooks are how database teams share tuning knowledge.
  Tools like MkDocs/Sphinx render structured sources into docs sites; generating Markdown
  from measurements keeps the numbers honest and current.

Trade-offs:
- A generator enforces consistency but constrains expression — freeform prose is more
  flexible for nuance. The pragmatic answer is hybrid: generate the numbers/tables,
  hand-write the narrative around them.
"""
