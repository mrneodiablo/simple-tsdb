#!/usr/bin/env python3
"""
Week 4 Integration Lab: API Layer (full system over a real socket)
=================================================================

This lab wires every Week 4 building block into a running server and drives it with
the client over a REAL loopback TCP socket — the one place in the curriculum where a
real port is used. It exercises the whole stack end to end:

    client -> frame (Day 22) -> protocol (Day 23) -> validate/route (Day 27)
           -> parse (Day 24) -> execute (Day 25) -> response -> client (Day 26)
    with per-request metrics (Day 28) collected server-side.

Scenario: A tiny TSDB service
Boot a server on 127.0.0.1:<ephemeral>, PING it, WRITE a batch of points, then run
QUERY statements (global, GROUP BY, WHERE) and verify results against a brute-force
ground truth. Finally, print the server's self-metrics.

Success Criteria:
- The client connects and PINGs successfully over a real socket
- Writes are accepted and stored
- Query results match a local brute-force computation
- A bad query returns a structured ServerError (not a crash)
- The server records per-operation latency/throughput metrics
- The server shuts down cleanly
"""

import os
import sys
import socket
import threading
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "exercises", "week4_api"))

try:
    from day22_tcp_server import serve_connection  # bytes-in/bytes-out over a socket
    from day24_query_parser import parse_query, ParseError
    from day25_execution_engine import ExecutionEngine, Query as EQuery, Condition as ECond
    from day26_client import Client
    from day27_error_handling import handle_request, QueryError
    from day28_monitoring import MetricsCollector
except ImportError as e:
    print(f"⚠️  Import Error: {e}")
    print("Complete Week 4 exercises (day22-day28) before running this lab.")
    sys.exit(1)


class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()


def build_server_handler(store: Dict[str, List[Dict[str, Any]]], metrics: MetricsCollector):
    """Return a bytes->bytes handler wiring protocol -> validate/route -> parse -> execute."""
    engine = ExecutionEngine(read_measurement=lambda name: list(store.get(name, [])))

    def write_handler(measurement, tags, fields, ts):
        point = {"measurement": measurement, "timestamp": ts or 0.0,
                 "tags": tags, "fields": fields}
        store.setdefault(measurement, []).append(point)

    def query_handler(q_text: str) -> List[Dict[str, Any]]:
        try:
            pq = parse_query(q_text)  # Day 24 AST
        except ParseError as e:
            raise QueryError(f"parse error: {e}")  # client's fault -> 422, not 500
        eq = EQuery(
            agg=pq.agg, field=pq.field, measurement=pq.measurement,
            conditions=[ECond(c.key, c.op, c.value, c.is_string) for c in pq.conditions],
            group_by=list(pq.group_by),
        )
        rs = engine.execute(eq)  # Day 25
        return [{**r.tags, "value": r.value} for r in rs.rows]

    def handler(req_bytes: bytes) -> bytes:
        text = req_bytes.decode("utf-8")
        parts = text.split()
        op = parts[1].upper() if len(parts) > 1 else "?"
        with metrics.measure(op):
            resp = handle_request(text, write_handler, query_handler)
        return resp.encode("utf-8")

    return handler


def start_server(handler):
    """Bind an ephemeral port, accept one connection in a daemon thread. Return (sock, port)."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    def accept_loop():
        try:
            conn, _ = srv.accept()
            with conn:
                serve_connection(conn, handler)
        except OSError:
            pass  # socket closed during shutdown

    t = threading.Thread(target=accept_loop, daemon=True)
    t.start()
    return srv, port, t


def run_integration_test():
    print("=" * 60)
    print("🧪 Week 4 Integration Lab: API Layer (real socket)")
    print("=" * 60)

    store: Dict[str, List[Dict[str, Any]]] = {}
    metrics = MetricsCollector(MonotonicClock())
    handler = build_server_handler(store, metrics)
    srv, port, thread = start_server(handler)
    print(f"🔌 Server listening on 127.0.0.1:{port}")

    # local dataset (also our ground truth)
    points = [
        ("cpu", {"host": "a", "region": "us"}, 10.0),
        ("cpu", {"host": "a", "region": "us"}, 30.0),
        ("cpu", {"host": "b", "region": "us"}, 100.0),
        ("cpu", {"host": "b", "region": "eu"}, 60.0),
        ("cpu", {"host": "c", "region": "eu"}, 50.0),
        ("cpu", {"host": "c", "region": "eu"}, 20.0),
    ]

    conn = socket.create_connection(("127.0.0.1", port))
    client = Client(conn)

    try:
        # ------------------------------------------------------------------
        print("\n" + "=" * 40 + "\nTest 1: PING\n" + "=" * 40)
        assert client.ping() is True
        print("✅ Server responded to PING")

        # ------------------------------------------------------------------
        print("\n" + "=" * 40 + "\nTest 2: WRITE batch\n" + "=" * 40)
        for i, (m, tags, val) in enumerate(points):
            ok = client.write(m, tags, {"value": val}, timestamp=1_700_000_000 + i)
            assert ok is True
        assert len(store["cpu"]) == len(points)
        print(f"✅ Wrote {len(points)} points; server stored {len(store['cpu'])}")

        # ------------------------------------------------------------------
        print("\n" + "=" * 40 + "\nTest 3: Global aggregate\n" + "=" * 40)
        rows = client.query("SELECT mean(value) FROM cpu")
        expected_mean = sum(v for _, _, v in points) / len(points)
        assert abs(rows[0]["value"] - expected_mean) < 1e-6
        print(f"✅ mean(value) = {rows[0]['value']} (expected {expected_mean})")

        # ------------------------------------------------------------------
        print("\n" + "=" * 40 + "\nTest 4: GROUP BY host\n" + "=" * 40)
        rows = client.query("SELECT mean(value) FROM cpu GROUP BY host")
        got = {r["host"]: round(r["value"], 4) for r in rows}
        truth: Dict[str, List[float]] = {}
        for _, tags, v in points:
            truth.setdefault(tags["host"], []).append(v)
        exp = {h: round(sum(vs) / len(vs), 4) for h, vs in truth.items()}
        assert got == exp, f"{got} != {exp}"
        print(f"✅ per-host mean = {got}")

        # ------------------------------------------------------------------
        print("\n" + "=" * 40 + "\nTest 5: WHERE filter\n" + "=" * 40)
        rows = client.query("SELECT count(value) FROM cpu WHERE region = 'eu'")
        exp_count = sum(1 for _, t, _ in points if t["region"] == "eu")
        assert rows[0]["value"] == exp_count
        print(f"✅ count where region='eu' = {rows[0]['value']} (expected {exp_count})")
        print("   table:\n" + Client.format_table(
            client.query("SELECT sum(value) FROM cpu GROUP BY region")))

        # ------------------------------------------------------------------
        print("\n" + "=" * 40 + "\nTest 6: Error handling\n" + "=" * 40)
        raised = False
        try:
            client.query("SELECT FROM")  # invalid query
        except Exception as e:
            raised = True
            print(f"✅ bad query raised: {e}")
        assert raised, "expected an error for a bad query"

        # ------------------------------------------------------------------
        print("\n" + "=" * 40 + "\nTest 7: Server metrics\n" + "=" * 40)
        q_stats = metrics.stats("QUERY")
        w_stats = metrics.stats("WRITE")
        assert q_stats.count >= 4 and w_stats.count == len(points)
        print(f"✅ QUERY: count={q_stats.count}, mean={q_stats.mean_latency*1e3:.2f}ms, "
              f"p95={ (q_stats.p95_latency or 0)*1e3:.2f}ms, throughput={q_stats.throughput:.0f}/s")
        print(f"✅ WRITE: count={w_stats.count}, mean={w_stats.mean_latency*1e3:.2f}ms")

    finally:
        conn.close()
        srv.close()
        thread.join(timeout=1.0)

    # ------------------------------------------------------------------
    print("\n" + "=" * 40 + "\nSummary\n" + "=" * 40)
    print(f"   Points stored:     {len(store.get('cpu', []))}")
    print(f"   Operations tracked:{metrics.operations()}")
    print("\n🎉 Week 4 Integration Lab Completed Successfully!")
    print("🚀 Ready to proceed to Week 5: Comparison & Analysis")
    return {"stored": len(store.get("cpu", [])), "ops": metrics.operations()}


if __name__ == "__main__":
    """
    Run this lab after completing Week 4 exercises (day22-day28).

    This lab will:
    1. Boot a TSDB server on an ephemeral loopback port in a background thread
    2. PING, WRITE a batch, and run QUERY statements over a real socket
    3. Verify query results against a brute-force ground truth
    4. Confirm a bad query surfaces as a structured error (no crash)
    5. Report the server's per-operation latency/throughput metrics
    6. Shut the server down cleanly

    Expected results:
    - All queries match the local computation
    - The bad query raises instead of hanging or crashing
    - Metrics show QUERY and WRITE operation counts and latencies
    """
    try:
        run_integration_test()
        print("\n✅ Lab completed successfully!")
        print("   Continue to Week 5: Comparison & Analysis")
    except Exception as e:
        print(f"\n❌ Lab failed with error: {e}")
        print("   Review your Week 4 implementations and try again")
        raise
