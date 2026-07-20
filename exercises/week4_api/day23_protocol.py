#!/usr/bin/env python3
"""
Day 23: Protocol Design (text request/response, versioning, errors)
==================================================================

Problem: Framing (Day 22) delivers whole messages; now you must decide what a
message MEANS. Design a small, human-readable, versioned text protocol: a request
names a command (PING / WRITE / QUERY) plus arguments; a response carries a status
(OK / ERROR), an optional numeric code, and a body. A good protocol is unambiguous
to parse, easy to extend, and explicit about errors.

Learning Objectives:
- Design a line-oriented request/response format
- Version the protocol so clients and servers can evolve (TSDB/1)
- Parse a request into a structured command + args (preserving arg whitespace)
- Serialize/parse responses with status, code, and a multi-line body
- Signal malformed input with a dedicated ProtocolError

Real-World Connection:
InfluxDB's HTTP API is a versioned request/response protocol (`/api/v2/...`, status
codes, JSON bodies). Redis's RESP and SMTP/HTTP status-line design inspire this: a
status token, a code, then a body. Versioning in the first token is how protocols
avoid breaking old clients.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


PROTOCOL_VERSION = "TSDB/1"


class ProtocolError(Exception):
    """Raised when a request or response is malformed / uses a bad version."""


class Command(str, Enum):
    PING = "PING"
    WRITE = "WRITE"
    QUERY = "QUERY"


class Status(str, Enum):
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class Request:
    """A parsed request: a command plus the raw argument string (may be empty)."""
    command: Command
    args: str = ""


@dataclass
class Response:
    """A parsed response: status, numeric code, and a list of body lines."""
    status: Status
    code: int = 0
    body: List[str] = field(default_factory=list)


def build_request(command: Command, args: str = "") -> str:
    """
    Serialize a request line:  "TSDB/1 <COMMAND> <args>"
    (No trailing space when args is empty.)
    """
    # TODO: join version + command.value + args (omit the trailing space if no args)
    raise NotImplementedError


def parse_request(text: str) -> Request:
    """
    Parse a request line into a Request.

    Format: "<version> <COMMAND> <args...>"
      - Split into at most 3 parts on whitespace: version, command, args-rest.
      - The args-rest keeps its internal spaces intact (a query has spaces!).
      - Raise ProtocolError if: empty, wrong version, or unknown command.
      - Command matching is case-insensitive (normalize to upper).
    """
    # TODO: strip the trailing newline; split with maxsplit=2; validate version;
    #       map the command token to Command (ProtocolError if unknown); return Request
    raise NotImplementedError


def format_response(resp: Response) -> str:
    """
    Serialize a Response to text:
      Line 1: "TSDB/1 OK"           (code omitted when status OK and code == 0)
              "TSDB/1 ERROR 400"    (code shown for errors / non-zero)
      Lines 2..: each body line, one per line.

    Lines are joined with "\\n". No trailing newline.
    """
    # TODO: build the status line (include code when ERROR or code != 0), then append
    #       body lines; return "\n".join(...)
    raise NotImplementedError


def parse_response(text: str) -> Response:
    """
    Parse a response (client side) back into a Response.
      - First line: "<version> <STATUS> [code]". Validate version; map STATUS;
        parse code if present (default 0).
      - Remaining lines form the body list (empty list if none).
      - Raise ProtocolError on bad version or unknown status.
    """
    # TODO: split into lines; parse the status line; collect the rest as body
    raise NotImplementedError


def test_protocol():
    print("Testing Protocol Design...")

    # Test 1: build + parse a simple request
    assert build_request(Command.PING) == "TSDB/1 PING"
    req = parse_request("TSDB/1 PING")
    assert req.command == Command.PING and req.args == ""
    print("✓ Test 1 passed: PING request round-trip")

    # Test 2: QUERY args preserve internal spaces
    line = build_request(Command.QUERY, "SELECT mean(value) FROM cpu WHERE region = 'us'")
    req = parse_request(line)
    assert req.command == Command.QUERY
    assert req.args == "SELECT mean(value) FROM cpu WHERE region = 'us'"
    print("✓ Test 2 passed: QUERY args preserved")

    # Test 3: case-insensitive command
    assert parse_request("TSDB/1 write cpu,host=a value=1").command == Command.WRITE
    print("✓ Test 3 passed: case-insensitive command")

    # Test 4: bad version rejected
    for bad in ["", "HTTP/1 PING", "TSDB/2 PING"]:
        try:
            parse_request(bad)
            assert False, f"expected ProtocolError for {bad!r}"
        except ProtocolError:
            pass
    print("✓ Test 4 passed: bad version rejected")

    # Test 5: unknown command rejected
    try:
        parse_request("TSDB/1 DELETE cpu")
        assert False, "expected ProtocolError for unknown command"
    except ProtocolError:
        pass
    print("✓ Test 5 passed: unknown command rejected")

    # Test 6: OK response with body round-trips
    resp = Response(Status.OK, 0, ["row1", "row2"])
    text = format_response(resp)
    assert text.splitlines()[0] == "TSDB/1 OK"
    back = parse_response(text)
    assert back.status == Status.OK and back.code == 0 and back.body == ["row1", "row2"]
    print("✓ Test 6 passed: OK response round-trip")

    # Test 7: ERROR response shows code + message
    resp = Response(Status.ERROR, 400, ["bad query: unexpected token"])
    text = format_response(resp)
    assert text.splitlines()[0] == "TSDB/1 ERROR 400"
    back = parse_response(text)
    assert back.status == Status.ERROR and back.code == 400
    assert back.body == ["bad query: unexpected token"]
    print("✓ Test 7 passed: ERROR response round-trip")

    # Test 8: empty-body OK response
    text = format_response(Response(Status.OK))
    assert text == "TSDB/1 OK"
    assert parse_response(text).body == []
    print("✓ Test 8 passed: empty-body response")

    print("\n🎉 All protocol tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement build_request, parse_request, format_response, parse_response.
    2. Run: python day23_protocol.py
    3. All 8 tests should pass.

    Success criteria:
    - Requests round-trip; query args keep their internal spaces
    - Bad versions and unknown commands raise ProtocolError
    - Responses carry status + code + body and round-trip exactly

    Next steps:
    - Day 24: parse the QUERY args string into a structured query (lexer + parser).
    - Think about: why put the version FIRST in every message?
    """
    test_protocol()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Protocol = Agreement on Meaning
   - Framing says "here is a message"; the protocol says "here is what it requests and
     how the answer is shaped". Keep it unambiguous to parse and cheap to extend.

2. Versioning
   - A leading version token (TSDB/1) lets a server support old and new clients and
     lets clients detect an incompatible peer immediately. Version FIRST so it's the
     very first thing both sides read.

3. Status + Code + Body
   - Borrowed from HTTP/SMTP: a machine-readable status (OK/ERROR) and numeric code
     for programmatic handling, plus a human-readable body. Errors are first-class,
     not an afterthought — the client always knows success from failure.

4. Text vs Binary
   - Text protocols are debuggable (telnet/nc, eyeball the wire) and easy to teach;
     binary protocols are compact and fast. Redis chose text-ish RESP for exactly the
     debuggability reason — a good trade for a learning DB.

Connection to InfluxDB:
- InfluxDB's HTTP API is a versioned request/response protocol with status codes and
  structured bodies. Line protocol (Week 1) is the WRITE payload format that rides
  inside such requests — the same layering you have here (frame -> protocol -> query).

Trade-offs:
- A line-oriented text protocol is simple but must escape or length-delimit payloads
  containing newlines (our WRITE/QUERY args are single-line, so we sidestep it). Real
  protocols either forbid embedded newlines or fall back to length-prefixed bodies.
"""
