"""
API / Server Layer for Time-Series Database
==========================================

TCP framing, a versioned text protocol, a SQL-like query parser, a query execution
engine, request validation/error handling, a client, and lightweight monitoring.
Re-exports each module's public API, e.g. `from tsdb.server import Client, parse_query`.

(Note: the query execution AST — Query/Condition — is re-exported from execution_engine;
the parser's own Query/Condition are reached via `parse_query` / `Parser`.)
"""

from .tcp_server import encode_frame, FrameDecoder, serve_connection
from .query_parser import parse_query, tokenize, Parser, ParseError, TokType, Token
from .protocol import (
    ProtocolError, Command, Status, Request, Response,
    build_request, parse_request, format_response, parse_response,
)
from .client import Client, ServerError
from .error_handling import (
    ErrorCode, ApiError, ValidationError, NotFoundError, QueryError,
    make_ok, make_error, validate_write, validate_query, handle_request,
)
from .execution_engine import ExecutionEngine, Query, Condition, Row, ResultSet
from .monitoring import MetricsCollector, OpStats

__all__ = [
    # tcp_server (framing)
    "encode_frame", "FrameDecoder", "serve_connection",
    # query_parser
    "parse_query", "tokenize", "Parser", "ParseError", "TokType", "Token",
    # protocol
    "ProtocolError", "Command", "Status", "Request", "Response",
    "build_request", "parse_request", "format_response", "parse_response",
    # client
    "Client", "ServerError",
    # error_handling
    "ErrorCode", "ApiError", "ValidationError", "NotFoundError", "QueryError",
    "make_ok", "make_error", "validate_write", "validate_query", "handle_request",
    # execution_engine (the query AST + executor)
    "ExecutionEngine", "Query", "Condition", "Row", "ResultSet",
    # monitoring
    "MetricsCollector", "OpStats",
]
