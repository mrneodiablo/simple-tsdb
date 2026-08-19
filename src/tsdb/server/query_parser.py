#!/usr/bin/env python3

from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional


class ParseError(Exception):
    """Raised on malformed query text (lexing or parsing)."""


AGG_FUNCS = {"mean", "sum", "count", "min", "max"}
KEYWORDS = {"select", "from", "where", "and", "group", "by"}
OPERATORS = {"=", "!=", "<", "<=", ">", ">="}


class TokType(str, Enum):
    KEYWORD = "KEYWORD"
    IDENT = "IDENT"
    NUMBER = "NUMBER"
    STRING = "STRING"
    OP = "OP"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COMMA = "COMMA"


@dataclass
class Token:
    type: TokType
    value: Any


@dataclass
class Condition:
    key: str
    op: str
    value: Any               # str for quoted literals, float/int for numbers
    is_string: bool = False  # True if the literal was quoted


@dataclass
class Query:
    agg: str
    field: str
    measurement: str
    conditions: List[Condition] = field(default_factory=list)  # AND-joined
    group_by: List[str] = field(default_factory=list)


# Scanner spec: (TokType, regex). Order matters (longest operators first).
_TOKEN_SPEC = [
    (TokType.STRING, r"'[^']*'"),
    (TokType.NUMBER, r"-?\d+(?:\.\d+)?"),
    (TokType.OP,     r"!=|<=|>=|=|<|>"),
    (TokType.LPAREN, r"\("),
    (TokType.RPAREN, r"\)"),
    (TokType.COMMA,  r","),
    (TokType.IDENT,  r"[A-Za-z_][A-Za-z0-9_]*"),
]
_MASTER_RE = re.compile("|".join(f"(?P<{t.name}>{p})" for t, p in _TOKEN_SPEC))


def tokenize(text: str) -> List[Token]:
    """
    Scan `text` into a list of Tokens (no trailing EOF token — the parser tracks end
    by index).

    For each match:
      - STRING  -> strip the surrounding quotes, value is the inner text
      - NUMBER  -> int if it has no '.', else float
      - IDENT   -> if lowercase is a keyword, emit TokType.KEYWORD (value=lowercased);
                   else TokType.IDENT (value=original text)
      - others  -> value is the matched text
    Whitespace between tokens is skipped. Any unmatched character -> ParseError.
    """
    # TODO: iterate _MASTER_RE.finditer over the text, skipping whitespace, building
    #       Tokens per the rules above; raise ParseError on an unexpected character.

    tokens = []
    pos = 0
    while pos < len(text):
        match = _MASTER_RE.match(text, pos)
        if match:
            typ = match.lastgroup
            val = match.group(typ)
            if typ == "STRING":
                val = val[1:-1]  # strip quotes
            elif typ == "NUMBER":
                val = int(val) if "." not in val else float(val)
            elif typ == "IDENT":
                if val.lower() in KEYWORDS:
                    typ = "KEYWORD"
                    val = val.lower()
            tokens.append(Token(TokType(typ), val))
            pos = match.end()
        elif text[pos].isspace():
            pos += 1
        else:
            raise ParseError(f"unexpected character: {text[pos]!r}")
    return tokens


class Parser:
    """Recursive-descent parser over a token list."""

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    # --- cursor helpers -----------------------------------------------------
    def _peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self) -> Token:
        tok = self._peek()
        if tok is None:
            raise ParseError("unexpected end of query")
        self.pos += 1
        return tok

    def _expect(self, ttype: TokType) -> Token:
        tok = self._next()
        if tok.type != ttype:
            raise ParseError(f"expected {ttype.value}, got {tok.type.value} ({tok.value!r})")
        return tok

    def _expect_keyword(self, kw: str) -> None:
        tok = self._next()
        if tok.type != TokType.KEYWORD or tok.value != kw:
            raise ParseError(f"expected keyword {kw.upper()!r}, got {tok.value!r}")

    # --- grammar rules ------------------------------------------------------
    def parse(self) -> Query:
        """Parse a full query and ensure all tokens are consumed."""
        # TODO: SELECT agg '(' field ')' FROM measurement [where] [groupby];
        #       then assert self.pos == len(self.tokens) (else ParseError: trailing tokens)

        self._expect_keyword("select")
        agg, field = self._parse_select()
        self._expect_keyword("from")
        measurement = self._expect(TokType.IDENT).value
        conditions = self._parse_where()
        group_by = self._parse_group_by()
        if self._peek() is not None:
            raise ParseError(f"trailing tokens: {self._peek().value!r}")
        return Query(agg=agg, field=field, measurement=measurement, conditions=conditions, group_by=group_by)

    def _parse_select(self) -> tuple:
        """Parse `SELECT agg '(' IDENT ')'` -> (agg, field). Validate agg in AGG_FUNCS."""
        # TODO
        agg_tok = self._expect(TokType.IDENT)
        agg = agg_tok.value
        if agg not in AGG_FUNCS:
            raise ParseError(f"unknown aggregation function: {agg!r}")
        self._expect(TokType.LPAREN)
        field_tok = self._expect(TokType.IDENT)
        self._expect(TokType.RPAREN)
        return agg, field_tok.value

    def _parse_where(self) -> List[Condition]:
        """Parse `WHERE condition (AND condition)*` -> list of Conditions."""
        # TODO: only enter if the next token is the WHERE keyword; else return []
        conditions = []
        if self._peek() and self._peek().type == TokType.KEYWORD and self._peek().value == "where":
            self._expect_keyword("where")
            conditions.append(self._parse_condition())
            while self._peek() and self._peek().type == TokType.KEYWORD and self._peek().value == "and":
                self._expect_keyword("and")
                conditions.append(self._parse_condition())
        return conditions

    def _parse_condition(self) -> Condition:
        """Parse `IDENT op literal` -> Condition (is_string set for quoted literals)."""
        # TODO
        key_tok = self._expect(TokType.IDENT)
        op_tok = self._expect(TokType.OP)
        literal_tok = self._next()
        if literal_tok.type == TokType.STRING:
            value = literal_tok.value
            is_string = True
        elif literal_tok.type == TokType.NUMBER:
            value = literal_tok.value
            is_string = False
        else:
            raise ParseError(f"expected STRING or NUMBER, got {literal_tok.type.value} ({literal_tok.value!r})")
        return Condition(key=key_tok.value, op=op_tok.value, value=value, is_string=is_string)

    def _parse_group_by(self) -> List[str]:
        """Parse `GROUP BY IDENT (',' IDENT)*` -> list of tag names (or [] if absent)."""
        # TODO: only enter if the next token is the GROUP keyword; else return []
        group_by = []
        if self._peek() and self._peek().type == TokType.KEYWORD and self._peek().value == "group":
            self._expect_keyword("group")
            self._expect_keyword("by")
            group_by.append(self._expect(TokType.IDENT).value)
            while self._peek() and self._peek().type == TokType.COMMA:
                self._expect(TokType.COMMA)
                group_by.append(self._expect(TokType.IDENT).value)
        return group_by


def parse_query(text: str) -> Query:
    """Tokenize then parse `text` into a Query AST."""
    return Parser(tokenize(text)).parse()

