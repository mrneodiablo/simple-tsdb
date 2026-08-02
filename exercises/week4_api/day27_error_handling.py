#!/usr/bin/env python3
"""
Day 27: Error Handling & Validation (taxonomy + graceful failure)
================================================================

Problem: A server facing the network must never trust its input and never crash on a
bad request. Every failure needs a category (client's fault vs server's fault), a
stable numeric code, and a safe message — while unexpected internal errors must be
caught and sanitized so they don't leak stack traces or take the server down. Build a
small error taxonomy, input validators, and a request handler that maps every outcome
to a well-formed response.

Learning Objectives:
- Design an error taxonomy (400 bad request / 404 not found / 422 / 500 internal)
- Validate WRITE payloads and QUERY text before acting on them
- Convert exceptions into structured error responses (never propagate raw)
- Distinguish client errors (safe to echo) from internal errors (sanitize!)
- Keep the handler total: every input yields a valid response

Real-World Connection:
InfluxDB returns 400 for malformed line protocol, 404 for missing buckets, 422 for
unparseable queries, 500 for internal faults — and hides internals behind generic
messages. This client/server error contract is what makes an API safe to expose.
"""

from __future__ import annotations
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple


PROTOCOL_VERSION = "TSDB/1"


class ErrorCode(IntEnum):
    BAD_REQUEST = 400     # malformed protocol / invalid payload (client's fault)
    NOT_FOUND = 404       # unknown command / resource
    UNPROCESSABLE = 422   # well-formed but semantically invalid (e.g. bad query)
    INTERNAL = 500        # server bug / unexpected exception


class ApiError(Exception):
    """Base for all mapped errors: carries a numeric code and a safe message."""
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = int(code)
        self.message = message


class ValidationError(ApiError):
    def __init__(self, message: str):
        super().__init__(ErrorCode.BAD_REQUEST, message)


class NotFoundError(ApiError):
    def __init__(self, message: str):
        super().__init__(ErrorCode.NOT_FOUND, message)


class QueryError(ApiError):
    def __init__(self, message: str):
        super().__init__(ErrorCode.UNPROCESSABLE, message)


# --- response builders (GIVEN) ------------------------------------------------
def make_ok(body: Optional[List[str]] = None) -> str:
    lines = ["TSDB/1 OK"] + (body or [])
    return "\n".join(lines)


def make_error(code: int, message: str) -> str:
    return f"TSDB/1 ERROR {code}\n{message}"


# --- request parsing helpers (GIVEN) ------------------------------------------
def _split_request(text: str) -> Tuple[str, str]:
    """Return (COMMAND_UPPER, args) from 'TSDB/1 CMD args'. Raise ValidationError if malformed."""
    parts = text.strip().split(maxsplit=2)
    if len(parts) < 2 or parts[0] != PROTOCOL_VERSION:
        raise ValidationError("malformed request line")
    return parts[1].upper(), (parts[2] if len(parts) > 2 else "")


def _parse_write_args(args: str) -> Tuple[str, Dict[str, str], Dict[str, Any], Optional[float]]:
    """
    Parse 'measurement k=v,k=v k=v,k=v [ts]' into (measurement, tags, fields, ts).
    Field values are coerced: int/float if numeric, else the raw string. Raises
    ValidationError on structurally broken input (wrong number of sections).
    """
    parts = args.split()
    if len(parts) < 3:
        raise ValidationError("WRITE needs measurement, tags, and fields")

    def kv(section: str) -> Dict[str, str]:
        out = {}
        for pair in section.split(","):
            if "=" not in pair:
                raise ValidationError(f"bad key=value: {pair!r}")
            k, v = pair.split("=", 1)
            out[k] = v
        return out

    measurement = parts[0]
    tags = kv(parts[1])
    raw_fields = kv(parts[2])
    fields: Dict[str, Any] = {}
    for k, v in raw_fields.items():
        try:
            fields[k] = int(v)
        except ValueError:
            try:
                fields[k] = float(v)
            except ValueError:
                fields[k] = v
    ts = float(parts[3]) if len(parts) > 3 else None
    return measurement, tags, fields, ts


# --- IMPLEMENT: validators + handler ------------------------------------------
def validate_write(measurement: str, tags: Dict[str, str], fields: Dict[str, Any]) -> None:
    """
    Validate a parsed WRITE. Raise ValidationError (400) on any problem:
      - measurement must be a non-empty string
      - every tag key must be non-empty; every tag VALUE must be a str
      - fields must be non-empty
      - every field value must be int / float / bool / str (nothing else)
    Return None if valid.
    """
    # TODO: check each rule above and raise ValidationError with a clear message.
    if not isinstance(measurement, str) or not measurement.strip():
        raise ValidationError("measurement must be a non-empty string")
    for k, v in tags.items():
        if not isinstance(k, str) or not k.strip():
            raise ValidationError(f"tag key must be a non-empty string: {k!r}")
        if not isinstance(v, str):
            raise ValidationError(f"tag value must be a string: {v!r}")
    if not fields:
        raise ValidationError("fields must be non-empty")
    for k, v in fields.items():
        if not isinstance(v, (int, float, bool, str)):
            raise ValidationError(f"field value must be int/float/bool/str: {v!r}")
    return None


def validate_query(q: str) -> None:
    """
    Validate QUERY text. Raise QueryError (422) if:
      - it is empty / whitespace only
      - it does not contain both SELECT and FROM (case-insensitive)
    Return None if it passes this basic sanity check.
    """
    # TODO: implement the checks above.
    if not isinstance(q, str) or not q.strip():
        raise QueryError("query must be a non-empty string")
    q_upper = q.upper()
    if "SELECT" not in q_upper or "FROM" not in q_upper:
        raise QueryError("query must contain both SELECT and FROM")
    return None


def handle_request(
    text: str,
    write_handler: Callable[[str, Dict[str, str], Dict[str, Any], Optional[float]], None],
    query_handler: Callable[[str], List[Dict[str, Any]]],
) -> str:
    """
    Total request handler: parse, validate, dispatch, and ALWAYS return a valid
    response string. Rules:
      - PING             -> make_ok()
      - WRITE  <args>    -> parse + validate_write + write_handler(...) -> make_ok()
      - QUERY  <q>       -> validate_query + query_handler(q); format each row dict as
                            space-joined "k=v" -> make_ok(rows)
      - anything else    -> NotFoundError
    Error mapping (wrap the whole body in try/except):
      - ApiError  -> make_error(e.code, e.message)          (client-safe message)
      - any other Exception -> make_error(500, "internal error")   (SANITIZED — never
        leak the exception text/stack)
    """
    # TODO: dispatch on the command; wrap in try/except to map ApiError vs unexpected
    #       Exception per the rules above. Never let an exception escape this function.

    try:
        command, args = _split_request(text)
        if command == "PING":
            return make_ok()
        elif command == "WRITE":
            measurement, tags, fields, ts = _parse_write_args(args)
            validate_write(measurement, tags, fields)
            write_handler(measurement, tags, fields, ts)
            return make_ok()
        elif command == "QUERY":
            validate_query(args)
            rows = query_handler(args)
            lines = [_row_to_line(row) for row in rows]
            return make_ok(lines)
        else:
            raise NotFoundError(f"unknown command: {command}")
    except ApiError as e:
        return make_error(e.code, e.message)
    except Exception:
        return make_error(ErrorCode.INTERNAL, "internal error")


def _row_to_line(row: Dict[str, Any]) -> str:
    """Serialize a result row dict as space-joined k=v (helper for QUERY responses)."""
    return " ".join(f"{k}={v}" for k, v in row.items())


def test_error_handling():
    print("Testing Error Handling & Validation...")

    # Test 1: validate_write accepts a good payload
    validate_write("cpu", {"host": "a"}, {"value": 10, "ok": True})
    print("✓ Test 1 passed: valid write accepted")

    # Test 2: empty measurement rejected
    for bad in [("", {"host": "a"}, {"value": 1})]:
        try:
            validate_write(*bad)
            assert False
        except ValidationError:
            pass
    print("✓ Test 2 passed: empty measurement rejected")

    # Test 3: non-string tag value rejected
    try:
        validate_write("cpu", {"host": 123}, {"value": 1})  # type: ignore
        assert False
    except ValidationError:
        pass
    print("✓ Test 3 passed: non-string tag value rejected")

    # Test 4: empty fields rejected
    try:
        validate_write("cpu", {"host": "a"}, {})
        assert False
    except ValidationError:
        pass
    print("✓ Test 4 passed: empty fields rejected")

    # Test 5: validate_query basic checks
    validate_query("SELECT mean(value) FROM cpu")
    for bad in ["", "   ", "DROP TABLE cpu", "SELECT mean(value)"]:
        try:
            validate_query(bad)
            assert False, f"expected QueryError for {bad!r}"
        except QueryError:
            pass
    print("✓ Test 5 passed: query validation")

    # Handlers for the dispatcher
    writes = []
    def wh(m, t, f, ts): writes.append((m, t, f, ts))
    def qh(q): return [{"host": "a", "value": 20.0}, {"host": "b", "value": 100.0}]

    # Test 6: PING and WRITE dispatch
    assert handle_request("TSDB/1 PING", wh, qh) == "TSDB/1 OK"
    resp = handle_request("TSDB/1 WRITE cpu host=a value=10 1700000000", wh, qh)
    assert resp == "TSDB/1 OK" and writes and writes[0][0] == "cpu"
    print("✓ Test 6 passed: PING + WRITE dispatch")

    # Test 7: QUERY dispatch formats rows
    resp = handle_request("TSDB/1 QUERY SELECT mean(value) FROM cpu GROUP BY host", wh, qh)
    lines = resp.split("\n")
    assert lines[0] == "TSDB/1 OK"
    assert "host=a" in lines[1] and "value=20.0" in lines[1]
    print("✓ Test 7 passed: QUERY response formatting")

    # Test 8: validation error -> 400; unknown command -> 404
    r400 = handle_request("TSDB/1 WRITE cpu host=a", wh, qh)  # missing fields section
    assert r400.startswith("TSDB/1 ERROR 400")
    r404 = handle_request("TSDB/1 DELETE cpu", wh, qh)
    assert r404.startswith("TSDB/1 ERROR 404")
    print("✓ Test 8 passed: 400 + 404 mapping")

    # Test 9: unexpected exception in a handler -> sanitized 500
    def boom(q): raise RuntimeError("secret internal detail: db path /etc/...")
    r500 = handle_request("TSDB/1 QUERY SELECT x FROM y", wh, boom)
    assert r500.startswith("TSDB/1 ERROR 500")
    assert "secret" not in r500 and "internal error" in r500
    print("✓ Test 9 passed: internal error sanitized")

    print("\n🎉 All error handling tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement validate_write, validate_query, and handle_request.
    2. Run: python day27_error_handling.py
    3. All 9 tests should pass.

    Success criteria:
    - Validators reject bad input with ValidationError/QueryError and clear messages
    - handle_request is TOTAL: every input returns a valid TSDB/1 response
    - Client errors map to 400/404/422; unexpected errors map to a sanitized 500
    - No internal exception text ever leaks to the client

    Next steps:
    - Day 28: measure the server — per-request latency, throughput, error rates.
    - Think about: why is leaking a stack trace to a client a security problem?
    """
    test_error_handling()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Error Taxonomy
   - Categorizing failures (4xx client vs 5xx server) tells the caller who must fix
     what and lets clients react programmatically (retry a 500, don't retry a 400).
     Stable codes are part of the API contract.

2. Validate at the Boundary
   - Untrusted input is checked ONCE, at the edge, before it reaches business logic.
     Everything downstream can then assume clean data — a huge simplification and a
     security necessity.

3. Total Handlers
   - handle_request never throws and never crashes the server: every path — success,
     client error, or internal bug — produces a valid response. A try/except around the
     dispatch body guarantees this.

4. Sanitizing Internal Errors
   - Client errors carry a helpful message; internal errors are logged server-side but
     returned as a generic 500. Echoing exception text leaks implementation details
     (paths, versions, SQL) that attackers use — so internal messages are hidden.

Connection to InfluxDB:
- InfluxDB maps malformed line protocol to 400, missing resources to 404, bad queries
  to 422, and internal faults to 500 with generic bodies — the same contract you built.

Trade-offs:
- Strict up-front validation adds a little latency and can reject edge cases a lenient
  server would accept. But "fail fast with a clear code" beats "accept garbage and
  corrupt data later" — especially for a write path.
"""
