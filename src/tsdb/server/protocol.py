#!/usr/bin/env python3

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
    if args:
        return f"{PROTOCOL_VERSION} {command.value} {args}"
    else:
        return f"{PROTOCOL_VERSION} {command.value}"


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
    text = text.rstrip("\n")
    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        raise ProtocolError("Request must have at least version and command")
    version, command_token = parts[0], parts[1]
    args = parts[2] if len(parts) == 3 else ""
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"Unsupported protocol version: {version}")
    try:
        command = Command(command_token.upper())
    except ValueError:
        raise ProtocolError(f"Unknown command: {command_token}")
    return Request(command=command, args=args)


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
    status_line = f"{PROTOCOL_VERSION} {resp.status.value}"
    if resp.status == Status.ERROR or resp.code != 0:
        status_line += f" {resp.code}"
    return "\n".join([status_line] + resp.body)

def parse_response(text: str) -> Response:
    """
    Parse a response (client side) back into a Response.
      - First line: "<version> <STATUS> [code]". Validate version; map STATUS;
        parse code if present (default 0).
      - Remaining lines form the body list (empty list if none).
      - Raise ProtocolError on bad version or unknown status.
    """
    # TODO: split into lines; parse the status line; collect the rest as body
    lines = text.splitlines()
    if not lines:
        raise ProtocolError("Response is empty")
    status_line = lines[0]
    parts = status_line.split(maxsplit=2)
    if len(parts) < 2:
        raise ProtocolError("Status line must have at least version and status")
    version, status_token = parts[0], parts[1]
    code = int(parts[2]) if len(parts) == 3 else 0
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"Unsupported protocol version: {version}")
    try:
        status = Status(status_token.upper())
    except ValueError:
        raise ProtocolError(f"Unknown status: {status_token}")
    body = lines[1:] if len(lines) > 1 else []
    return Response(status=status, code=code, body=body)

