#!/usr/bin/env python3

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

