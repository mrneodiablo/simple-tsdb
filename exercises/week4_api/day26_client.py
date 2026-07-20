#!/usr/bin/env python3
"""
Day 26: Client Interface (connect, write, query, format results)
===============================================================

Problem: A database is only as usable as its client. Build a client library that
hides framing (Day 22) and the wire protocol (Day 23) behind friendly methods:
ping(), write(...), query(...). The client sends a framed request, reads the framed
response, interprets the status, and hands back Python data — turning bytes on a
socket into `[{"host": "a", "value": 20.0}, ...]`.

Learning Objectives:
- Wrap a transport with a request/response round-trip (framing given)
- Build protocol requests for PING / WRITE / QUERY
- Interpret responses: raise on ERROR, parse OK bodies into Python data
- Format a result set into a readable text table
- Keep the client transport-agnostic (inject a fake for tests)

Real-World Connection:
influxdb-client-python, redis-py, and psycopg all do this: manage the connection,
serialize requests, parse responses, and surface errors as exceptions. A clean client
is what makes a database pleasant to use — and what most engineers actually touch.
"""

from __future__ import annotations
import struct
from typing import Any, Dict, List, Optional, Protocol


PROTOCOL_VERSION = "TSDB/1"


class ServerError(Exception):
    """Raised when the server returns an ERROR response."""
    def __init__(self, code: int, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class Transport(Protocol):
    def recv(self, n: int) -> bytes: ...
    def sendall(self, data: bytes) -> None: ...


# --- Framing helpers (GIVEN — this is Day 22's lesson, reused here) ------------
def _encode_frame(payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + payload


def _recv_exactly(transport: Transport, n: int) -> bytes:
    """Read exactly n bytes (looping over recv). Raise ConnectionError on early close."""
    buf = bytearray()
    while len(buf) < n:
        chunk = transport.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed mid-frame")
        buf.extend(chunk)
    return bytes(buf)


class Client:
    """
    High-level client over an injected transport.

    Dependency injected:
      - transport: a socket-like object (recv/sendall). Use a fake in tests.
    """

    def __init__(self, transport: Transport):
        self.transport = transport

    # --- request/response round-trip (GIVEN) ----------------------------------
    def _request(self, text: str) -> str:
        """Send one framed request line, read one framed response, return its text."""
        self.transport.sendall(_encode_frame(text.encode("utf-8")))
        header = _recv_exactly(self.transport, 4)
        (length,) = struct.unpack(">I", header)
        payload = _recv_exactly(self.transport, length)
        return payload.decode("utf-8")

    # --- public API (IMPLEMENT THESE) -----------------------------------------
    def ping(self) -> bool:
        """Send PING; return True if the server responds OK, else False."""
        # TODO: build "TSDB/1 PING", send via _request, return True iff status is OK
        raise NotImplementedError

    def write(self, measurement: str, tags: Dict[str, str],
              fields: Dict[str, Any], timestamp: Optional[float] = None) -> bool:
        """
        Send a WRITE request. Serialize the point as a single-line argument:
            "<measurement> <k=v tags,comma-joined> <k=v fields,comma-joined> [ts]"
        e.g. WRITE cpu host=a,region=us value=10,ok=true 1700000000
        Return True on OK; raise ServerError on ERROR.
        """
        # TODO: build the WRITE args string, send "TSDB/1 WRITE <args>", check status
        #       (raise ServerError if the response status is ERROR).
        raise NotImplementedError

    def query(self, q: str) -> List[Dict[str, Any]]:
        """
        Send a QUERY request and parse the OK body into a list of row dicts.

        Body rows are space-separated key=value pairs, e.g.:
            "host=a value=20.0"
            "value=47.5"
        Parse each row into a dict; parse the "value" field as float when possible.
        Raise ServerError on an ERROR response.
        """
        # TODO: send "TSDB/1 QUERY <q>"; on ERROR raise ServerError; else parse each
        #       body line into a dict (split on spaces, then on '='), coercing floats.
        raise NotImplementedError

    @staticmethod
    def _parse_status(response_text: str) -> tuple:
        """Return (status_str, code, body_lines) from a response. (helper for the above)"""
        lines = response_text.split("\n")
        parts = lines[0].split()
        if not parts or parts[0] != PROTOCOL_VERSION:
            raise ServerError(500, f"bad response: {lines[0]!r}")
        status = parts[1] if len(parts) > 1 else ""
        code = int(parts[2]) if len(parts) > 2 else 0
        return status, code, lines[1:]

    @staticmethod
    def format_table(rows: List[Dict[str, Any]]) -> str:
        """
        Render rows as an aligned text table. Columns are the union of keys in
        first-seen order; each column is padded to its widest value. Returns a header
        line + one line per row (joined by "\\n"). Empty rows -> "(no results)".
        """
        # TODO: collect columns in first-seen order; compute width per column; build a
        #       header row + data rows padded with str.ljust; join with "\n".
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Fake transport that runs an in-process "server" handler (no sockets)
# ---------------------------------------------------------------------------
class FakeServerTransport:
    """
    Loopback transport: sendall() decodes the request frame, calls handler(text) to
    get a response string, and queues the framed response for recv().
    `handler` maps a request line -> response text.
    """
    def __init__(self, handler):
        self.handler = handler
        self._in = bytearray()
        self._out = bytearray()

    def sendall(self, data: bytes) -> None:
        self._in.extend(data)
        # decode any complete request frames and produce responses
        while len(self._in) >= 4:
            (length,) = struct.unpack(">I", self._in[:4])
            if len(self._in) < 4 + length:
                break
            req = bytes(self._in[4:4 + length]).decode("utf-8")
            del self._in[:4 + length]
            resp = self.handler(req).encode("utf-8")
            self._out.extend(_encode_frame(resp))

    def recv(self, n: int) -> bytes:
        if not self._out:
            return b""
        take = self._out[:n]
        del self._out[:n]
        return bytes(take)


def _demo_handler(req: str) -> str:
    """A tiny fake server for tests: understands PING / WRITE / QUERY."""
    parts = req.split(maxsplit=2)
    cmd = parts[1].upper() if len(parts) > 1 else ""
    if cmd == "PING":
        return "TSDB/1 OK"
    if cmd == "WRITE":
        return "TSDB/1 OK"
    if cmd == "QUERY":
        args = parts[2] if len(parts) > 2 else ""
        if "BADQ" in args:
            return "TSDB/1 ERROR 400\nparse error near BADQ"
        return "TSDB/1 OK\nhost=a value=20.0\nhost=b value=100.0"
    return "TSDB/1 ERROR 404\nunknown command"


def test_client():
    print("Testing Client Interface...")

    client = Client(FakeServerTransport(_demo_handler))

    # Test 1: ping
    assert client.ping() is True
    print("✓ Test 1 passed: ping OK")

    # Test 2: write returns True on OK
    assert client.write("cpu", {"host": "a", "region": "us"}, {"value": 10}) is True
    print("✓ Test 2 passed: write OK")

    # Test 3: write serializes tags + fields (capture the request line)
    captured = []
    def capture_handler(req: str) -> str:
        captured.append(req)
        return "TSDB/1 OK"
    Client(FakeServerTransport(capture_handler)).write(
        "cpu", {"host": "a", "region": "us"}, {"value": 10}, timestamp=1700000000)
    sent = captured[0]
    assert sent.startswith("TSDB/1 WRITE cpu ")
    assert "host=a" in sent and "region=us" in sent and "value=10" in sent
    assert sent.endswith(" 1700000000")
    print("✓ Test 3 passed: write serialization")

    # Test 4: query parses rows into dicts
    rows = client.query("SELECT mean(value) FROM cpu GROUP BY host")
    assert rows == [{"host": "a", "value": 20.0}, {"host": "b", "value": 100.0}]
    print("✓ Test 4 passed: query rows parsed")

    # Test 5: query value coerced to float
    assert isinstance(rows[0]["value"], float)
    print("✓ Test 5 passed: value coerced to float")

    # Test 6: ERROR response raises ServerError with code
    try:
        client.query("SELECT BADQ FROM cpu")
        assert False, "expected ServerError"
    except ServerError as e:
        assert e.code == 400 and "parse error" in e.message
    print("✓ Test 6 passed: ERROR -> ServerError")

    # Test 7: format_table renders header + rows
    table = Client.format_table([{"host": "a", "value": 20.0}, {"host": "b", "value": 100.0}])
    assert "host" in table and "value" in table
    assert "100.0" in table and len(table.splitlines()) == 3  # header + 2 rows
    print("✓ Test 7 passed: format_table")

    # Test 8: empty result table
    assert Client.format_table([]) == "(no results)"
    print("✓ Test 8 passed: empty table")

    print("\n🎉 All client interface tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement ping, write, query, and format_table (framing + _request are given).
    2. Run: python day26_client.py
    3. All 8 tests should pass.

    Success criteria:
    - ping/write/query round-trip through the injected transport
    - WRITE serializes tags and fields as comma-joined k=v groups
    - QUERY parses OK bodies into row dicts; ERROR raises ServerError
    - format_table aligns columns and handles the empty case

    Next steps:
    - Day 27: harden the server side — validate input, map failures to error codes.
    - Think about: why should the client raise on ERROR instead of returning None?
    """
    test_client()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. The Client Hides the Wire
   - Users call query("SELECT ..."), not "frame these bytes, read a length prefix,
     split a status line". Encapsulating framing + protocol behind methods is the whole
     point of a client library.

2. Errors as Exceptions
   - A failed query should raise (ServerError), not return a sentinel the caller might
     ignore. This mirrors psycopg/redis-py and makes misuse loud instead of silent.

3. Serialization Symmetry
   - write() serializes Python data to the wire; query() deserializes the wire back to
     Python. Keeping these two mirror images (and typed) avoids the classic bug where a
     number round-trips as a string.

4. Transport Injection
   - The client depends on a recv/sendall interface, not on `socket`. The FakeServer
     transport runs an entire request/response cycle in-process, so client behavior is
     unit-tested deterministically — real sockets wait for the lab.

Connection to InfluxDB:
- influxdb-client-python manages the HTTP connection, serializes writes as line
  protocol, sends Flux/InfluxQL queries, and parses tabular results into records —
  exactly the write/query/format responsibilities you implemented.

Trade-offs:
- One request per round-trip is simple but adds latency per call; real clients add
  connection pooling, pipelining, and batched writes. We keep one-shot calls for
  clarity — the lab shows the full round-trip over a real socket.
"""
