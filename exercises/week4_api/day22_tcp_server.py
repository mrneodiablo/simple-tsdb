#!/usr/bin/env python3
"""
Day 22: TCP Server Foundation (framing & connection handling)
=============================================================

Problem: A TCP socket is a raw byte STREAM — recv() gives you "some bytes", never
"one message". Two writes can arrive glued together, or one message can arrive split
across three reads. Before you can speak any protocol you must solve *framing*:
mark where each message begins and ends. Build length-prefixed framing plus a
connection loop that turns a byte stream into a request/response conversation.

Learning Objectives:
- Understand why TCP needs application-level framing (no message boundaries)
- Implement length-prefixed framing (4-byte big-endian length + payload)
- Write a stateful decoder that handles partial reads and coalesced frames
- Drive a connection as read-frame -> handle -> write-frame until close
- Keep it testable by injecting the transport (no real socket in unit tests)

Real-World Connection:
Redis (RESP), Kafka, and gRPC/HTTP2 all length-prefix their frames for exactly this
reason. InfluxDB's HTTP API leans on HTTP's own framing (Content-Length / chunked).
The FrameDecoder here is the same state machine every networked DB needs.
"""

from __future__ import annotations
import struct
from typing import Callable, List, Optional, Protocol


LENGTH_PREFIX = 4  # bytes; big-endian uint32 payload length


class Transport(Protocol):
    """Minimal socket-like interface so tests can inject a fake."""
    def recv(self, n: int) -> bytes: ...
    def sendall(self, data: bytes) -> None: ...


def encode_frame(payload: bytes) -> bytes:
    """
    Frame a payload: a 4-byte big-endian length header followed by the payload.
    Example: b"hi" -> b"\\x00\\x00\\x00\\x02hi"
    """
    # TODO: use struct.pack(">I", len(payload)) as the header, then append payload
    raise NotImplementedError


class FrameDecoder:
    """
    Stateful decoder. feed(chunk) appends raw bytes to an internal buffer and returns
    a list of every COMPLETE payload now available (possibly empty, possibly many).
    Leftover partial-frame bytes stay buffered for the next feed().
    """

    def __init__(self):
        self._buf = bytearray()

    def feed(self, chunk: bytes) -> List[bytes]:
        """
        Append chunk, then pull out as many complete frames as the buffer allows.

        Loop:
          - if fewer than LENGTH_PREFIX bytes buffered -> stop (need more)
          - read length = struct.unpack(">I", first 4 bytes)
          - if fewer than (4 + length) bytes buffered -> stop (payload incomplete)
          - else slice out the payload, drop those bytes from the buffer, append to out
        """
        # TODO: append chunk to self._buf, then extract complete frames per the loop
        raise NotImplementedError

    def pending_bytes(self) -> int:
        """How many bytes are buffered but not yet a complete frame (for tests/debug)."""
        return len(self._buf)


# A handler maps a request payload to a response payload (pure function -> testable).
Handler = Callable[[bytes], bytes]


def serve_connection(transport: Transport, handler: Handler, recv_size: int = 4096) -> int:
    """
    Run one connection to completion:
      - read chunks from transport.recv(recv_size)
      - decode frames; for each complete request frame, call handler(request)
        and send the framed response back via transport.sendall(encode_frame(resp))
      - stop when recv() returns b"" (peer closed the connection)
    Return the number of requests handled.
    """
    # TODO: create a FrameDecoder; loop on transport.recv until it returns b"";
    #       feed each chunk, handle every decoded frame, send framed responses,
    #       count handled requests, and return the count.
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Fakes for testing (no real sockets)
# ---------------------------------------------------------------------------
class FakeTransport:
    """
    A scripted transport. recv() replays `chunks` in order (then b"" = closed).
    sendall() records everything written so tests can decode the responses.
    """
    def __init__(self, chunks: List[bytes]):
        self._chunks = list(chunks)
        self.sent = bytearray()

    def recv(self, n: int) -> bytes:
        if self._chunks:
            return self._chunks.pop(0)
        return b""

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)


def test_tcp_server():
    print("Testing TCP Server Foundation...")

    # Test 1: encode_frame length prefix
    assert encode_frame(b"hi") == b"\x00\x00\x00\x02hi"
    assert encode_frame(b"") == b"\x00\x00\x00\x00"
    print("✓ Test 1 passed: encode_frame")

    # Test 2: decode a single complete frame
    dec = FrameDecoder()
    assert dec.feed(encode_frame(b"hello")) == [b"hello"]
    assert dec.pending_bytes() == 0
    print("✓ Test 2 passed: single frame decode")

    # Test 3: payload split across feeds (partial reads)
    dec = FrameDecoder()
    framed = encode_frame(b"abcdef")
    assert dec.feed(framed[:3]) == []          # only part of the header
    assert dec.feed(framed[3:6]) == []         # header done, partial payload
    assert dec.feed(framed[6:]) == [b"abcdef"] # completes
    print("✓ Test 3 passed: partial reads reassembled")

    # Test 4: two frames coalesced in one chunk
    dec = FrameDecoder()
    both = encode_frame(b"one") + encode_frame(b"two")
    assert dec.feed(both) == [b"one", b"two"]
    print("✓ Test 4 passed: coalesced frames split")

    # Test 5: leftover partial frame stays buffered
    dec = FrameDecoder()
    out = dec.feed(encode_frame(b"done") + encode_frame(b"xx")[:3])
    assert out == [b"done"] and dec.pending_bytes() == 3
    print("✓ Test 5 passed: partial trailing frame buffered")

    # Test 6: serve_connection echoes framed requests
    reqs = [encode_frame(b"ping"), encode_frame(b"pong")]
    ft = FakeTransport(reqs)
    n = serve_connection(ft, handler=lambda r: r.upper())
    assert n == 2
    replies = FrameDecoder().feed(bytes(ft.sent))
    assert replies == [b"PING", b"PONG"]
    print("✓ Test 6 passed: serve_connection round-trip")

    # Test 7: multiple frames arriving in one recv chunk are all handled
    ft = FakeTransport([encode_frame(b"a") + encode_frame(b"b") + encode_frame(b"c")])
    n = serve_connection(ft, handler=lambda r: r)
    assert n == 3
    print("✓ Test 7 passed: batched requests handled")

    # Test 8: immediate close -> zero requests, no crash
    ft = FakeTransport([])
    assert serve_connection(ft, handler=lambda r: r) == 0
    print("✓ Test 8 passed: clean close handled")

    print("\n🎉 All TCP server foundation tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement encode_frame, FrameDecoder.feed, and serve_connection.
    2. Run: python day22_tcp_server.py
    3. All 8 tests should pass.

    Success criteria:
    - Framing round-trips: decode(encode(x)) == x for any bytes
    - The decoder survives arbitrary chunk boundaries (partial + coalesced)
    - serve_connection handles many requests per connection and stops on close

    Next steps:
    - Day 23: design the request/response protocol that rides inside these frames.
    - Think about: why length-prefix instead of a newline delimiter? (Hint: binary
      payloads can contain your delimiter byte.)
    """
    test_tcp_server()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. TCP Is a Byte Stream
   - TCP guarantees ORDER and delivery, not message boundaries. recv(n) returns
     "up to n bytes whenever they arrive" — you must reconstruct messages yourself.

2. Length-Prefixed Framing
   - Prepend the payload size so the reader knows exactly how many bytes to collect
     before dispatching. Robust for binary data (unlike delimiter framing, which
     breaks if the delimiter appears in the payload and needs escaping).

3. Stateful Decoding
   - A decoder buffers bytes across reads and emits frames only when complete. This
     handles both fragmentation (one message over many reads) and coalescing (many
     messages in one read) with the same loop.

4. Dependency Injection for Testability
   - By programming against a Transport protocol and injecting a FakeTransport, the
     entire framing + connection loop is unit-tested with zero sockets, zero ports,
     zero flakiness. Real sockets only appear in the integration lab.

Connection to InfluxDB / others:
- RESP (Redis), Kafka wire protocol, and gRPC all length-prefix messages. HTTP does
  the same via Content-Length/chunked, which is how InfluxDB's HTTP API frames bodies.

Trade-offs:
- Length prefixing needs the full length up front (fine for request/response, awkward
  for unbounded streaming, where chunked framing wins). A 4-byte prefix caps a single
  frame at ~4 GiB — plenty here, but real servers also enforce a max-frame limit to
  avoid a malicious "length = 4 GiB" allocation attack.
"""
