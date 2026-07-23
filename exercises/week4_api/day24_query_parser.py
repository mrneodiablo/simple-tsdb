#!/usr/bin/env python3
"""
Day 24: Query Parser (lexer + recursive descent -> AST)
======================================================

Problem: The QUERY arguments from Day 23 arrive as one string:
"SELECT mean(value) FROM cpu WHERE region = 'us-west' AND value > 90 GROUP BY host".
To execute it you must turn that text into a structured, validated AST. Build a
two-stage parser: a LEXER that splits text into tokens, then a RECURSIVE-DESCENT
parser that consumes tokens according to a grammar and emits a Query object.

Learning Objectives:
- Tokenize with a scanner (keywords, identifiers, numbers, strings, operators)
- Write a recursive-descent parser: one function per grammar rule
- Build a typed AST (Query with select / from / where / group by)
- Distinguish string vs numeric literals during lexing
- Report clear errors on malformed input (ParseError)

Grammar (this exercise):
    query      := SELECT agg '(' IDENT ')' FROM IDENT [where] [groupby]
    agg        := mean | sum | count | min | max
    where      := WHERE condition (AND condition)*
    condition  := IDENT op literal
    op         := '=' | '!=' | '<' | '<=' | '>' | '>='
    literal    := STRING | NUMBER
    groupby    := GROUP BY IDENT (',' IDENT)*

Real-World Connection:
InfluxQL and SQL engines parse exactly this way: a lexer feeds a recursive-descent (or
generated) parser that builds an AST the planner then optimizes (your Week 3 Day 20!).
Flux is parsed to an AST too. This is the front door of every query engine.
"""

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


def test_query_parser():
    print("Testing Query Parser...")

    # Test 1: tokenize basics
    toks = tokenize("SELECT mean(value)")
    types = [t.type for t in toks]
    assert types == [TokType.KEYWORD, TokType.IDENT, TokType.LPAREN, TokType.IDENT, TokType.RPAREN]
    assert toks[0].value == "select"  # keyword lowercased
    print("✓ Test 1 passed: tokenize")

    # Test 2: minimal query
    q = parse_query("SELECT mean(value) FROM cpu")
    assert q.agg == "mean" and q.field == "value" and q.measurement == "cpu"
    assert q.conditions == [] and q.group_by == []
    print("✓ Test 2 passed: minimal query")

    # Test 3: single WHERE condition (string literal)
    q = parse_query("SELECT max(value) FROM cpu WHERE region = 'us-west'")
    assert len(q.conditions) == 1
    c = q.conditions[0]
    assert c.key == "region" and c.op == "=" and c.value == "us-west" and c.is_string
    print("✓ Test 3 passed: WHERE string condition")

    # Test 4: multiple AND conditions, numeric literal
    q = parse_query("SELECT mean(value) FROM cpu WHERE region = 'us' AND value > 90")
    assert len(q.conditions) == 2
    assert q.conditions[1].key == "value" and q.conditions[1].op == ">"
    assert q.conditions[1].value == 90 and q.conditions[1].is_string is False
    print("✓ Test 4 passed: AND conditions + numeric literal")

    # Test 5: GROUP BY multiple tags
    q = parse_query("SELECT count(value) FROM http GROUP BY host, region")
    assert q.agg == "count" and q.group_by == ["host", "region"]
    print("✓ Test 5 passed: GROUP BY")

    # Test 6: full query, all clauses
    q = parse_query(
        "SELECT mean(latency) FROM http WHERE status = 'error' AND latency >= 200 GROUP BY service"
    )
    assert q.agg == "mean" and q.field == "latency" and q.measurement == "http"
    assert len(q.conditions) == 2 and q.group_by == ["service"]
    assert q.conditions[1].value == 200
    print("✓ Test 6 passed: full query")

    # Test 7: float literal typing
    q = parse_query("SELECT sum(value) FROM cpu WHERE value < 3.5")
    assert q.conditions[0].value == 3.5 and isinstance(q.conditions[0].value, float)
    print("✓ Test 7 passed: float literal")

    # Test 8: malformed queries raise ParseError
    for bad in [
        "SELECT mean(value)",                 # missing FROM
        "mean(value) FROM cpu",               # missing SELECT
        "SELECT median(value) FROM cpu",      # unknown agg
        "SELECT mean value) FROM cpu",        # missing '('
        "SELECT mean(value) FROM cpu EXTRA",  # trailing tokens
    ]:
        try:
            parse_query(bad)
            assert False, f"expected ParseError for {bad!r}"
        except ParseError:
            pass
    print("✓ Test 8 passed: malformed queries rejected")

    print("\n🎉 All query parser tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement tokenize and the Parser grammar methods (and parse()).
    2. Run: python day24_query_parser.py
    3. All 8 tests should pass.

    Success criteria:
    - The lexer classifies keywords, idents, numbers, strings, and operators
    - The parser builds a correct Query AST for every clause combination
    - Numeric vs string literals are typed correctly
    - Malformed input raises ParseError (never a random KeyError/IndexError)

    Next steps:
    - Day 25: execute this Query AST against data (bind to Week 2/3 operators).
    - Think about: why separate lexing from parsing instead of one big regex?
    """
    test_query_parser()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Two-Stage Parsing (lex then parse)
   - The lexer turns characters into tokens (a flat, typed stream); the parser turns
     tokens into a tree. Separating them keeps each simple: the parser never worries
     about whitespace or how a number is spelled.

2. Recursive-Descent Parsing
   - One function per grammar rule, calling sub-rules. The call stack mirrors the
     grammar, so the code reads like the spec. A cursor (pos) + expect() helpers make
     "consume this token or error" trivial.

3. Typed AST
   - The output is data the next stage can inspect and optimize — the same "data not
     code" theme as Day 15's predicate tree and Day 20's plan. Typing literals at parse
     time (int/float/str) saves the executor from guessing later.

4. Error Reporting
   - Good parsers fail with a specific message ("expected FROM, got IDENT") instead of
     an IndexError. expect()/expect_keyword() centralize that so every rule benefits.

Connection to InfluxDB:
- InfluxQL is lexed and parsed into an AST, then planned/executed; Flux compiles to an
  AST too. The AST is the hand-off point between "understanding the query" and
  "running it" — exactly the boundary between Day 24 and Day 25.

Trade-offs:
- Recursive descent is easy to write and debug but handrolls precedence/associativity
  (we sidestepped it by allowing only AND). Parser generators (yacc/ANTLR) scale to
  full SQL grammars but add tooling and are harder to teach from scratch.
"""
