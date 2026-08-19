#!/usr/bin/env python3

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
        response = self._request("TSDB/1 PING")
        status, code, body_lines = self._parse_status(response)
        return status == "OK"
        


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
        tag_str = ",".join(f"{k}={v}" for k, v in tags.items())
        field_str = ",".join(f"{k}={v}" for k, v in fields.items())
        args = f"{measurement} {tag_str} {field_str}"
        if timestamp is not None:
            args += f" {int(timestamp)}"
        response = self._request(f"TSDB/1 WRITE {args}")
        status, code, body_lines = self._parse_status(response)
        if status == "ERROR":
            raise ServerError(code, "\n".join(body_lines))
        return status == "OK"

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
        response = self._request(f"TSDB/1 QUERY {q}")
        status, code, body_lines = self._parse_status(response)
        if status == "ERROR":
            raise ServerError(code, "\n".join(body_lines))
        rows = []
        for line in body_lines:
            row = {}
            for pair in line.split():
                key, value = pair.split("=", 1)
                if key == "value":
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                row[key] = value
            rows.append(row)
        return rows

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
        if not rows:
            return "(no results)"
        # Collect columns in first-seen order
        columns = []
        for row in rows:
            for key in row.keys():
                if key not in columns:
                    columns.append(key)
        # Compute width per column
        col_widths = {col: len(col) for col in columns}
        for row in rows:
            for col in columns:
                value = str(row.get(col, ""))
                col_widths[col] = max(col_widths[col], len(value))
        # Build header row
        header = " | ".join(col.ljust(col_widths[col]) for col in columns)
        # Build data rows
        data_rows = []
        for row in rows:
            data_row = " | ".join(str(row.get(col, "")).ljust(col_widths[col]) for col in columns)
            data_rows.append(data_row)
        return "\n".join([header] + data_rows)

