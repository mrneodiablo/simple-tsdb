#!/usr/bin/env python3
"""
Day 3: Line Protocol Parser
==========================

Problem: Parse InfluxDB line protocol format into structured data

Learning Objectives:
- Understand protocol design principles
- Handle string parsing and tokenization
- Deal with escaping and special characters
- Implement robust error handling

Real-World Connection:
InfluxDB line protocol is optimized for fast parsing and compact representation.
Understanding protocol design helps you make better API design decisions.

Line Protocol Format:
measurement[,tag_key=tag_value[,tag_key=tag_value]] field_key=field_value[,field_key=field_value] [timestamp]

Examples:
cpu,host=server01 usage=23.5 1609459200000000000
http,endpoint=/api,method=GET response_time=150,status_code=200i 1609459200000000000

┌─────────────────┬──────────────────────┬────────────────────┐
│ Component       │ Allowed Characters   │ Can Escape?        │
├─────────────────┼──────────────────────┼────────────────────┤
│ Measurement     │ [a-zA-Z0-9_-]        │ NO                 │
│ Tag Key         │ [a-zA-Z0-9_-]        │ NO                 │
│ Tag Value       │ ANY (except ,= )     │ YES (\, \= \ )     │
│ Field Key       │ [a-zA-Z0-9_-]        │ NO                 │
│ Field Value     │ Depends on type      │ YES (if string)    │
└─────────────────┴──────────────────────┴────────────────────┘

InfluxDB Specification (actual):
https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/
"""

import re
import time
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class ParseError(Exception):
    """Raised when line protocol parsing fails."""

    def __init__(self, message: str, position: int = -1, line: str = ""):
        self.message = message
        self.position = position
        self.line = line
        super().__init__(f"Parse error at position {position}: {message}")


@dataclass
class ParsedPoint:
    """Result of parsing a line protocol string."""

    measurement: str
    tags: Dict[str, str]
    fields: Dict[str, Union[int, float, str, bool]]
    timestamp: Optional[float] = None


class FieldType(Enum):
    """Field value types in line protocol."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"


class LineProtocolParser:
    """
    Parses InfluxDB line protocol format.

    Handles:
    - Measurement names (NO escaping allowed)
    - Tag key-value pairs (keys: NO escaping, values: YES escaping)
    - Field key-value pairs with type detection (keys: NO escaping, string values: YES escaping)
    - Timestamp parsing (various precisions)
    - Character escaping in VALUES only
    - Error recovery and reporting
    """

    def __init__(self):
        """Initialize parser with configuration."""
        # TODO: Initialize any needed regex patterns or configuration
        # Consider: What patterns will you need for parsing different components?

        # Compiled regex patterns for validation
        # Allows: letters, numbers, underscores, hyphens
        # Does not allow: spaces, commas, equals, special chars
        self.measurement_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")
        self.tag_key_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")
        self.field_key_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")

        # Split line protocol (handles quoted strings)
        # Splits on spaces NOT inside quotes
        self.split_protocol_pattern = r'(?<!\\)\s+(?=(?:[^"]*"[^"]*")*[^"]*$)'

        # Split tags (handles escaped commas)
        # Splits on commas NOT preceded by backslash
        self.tag_split_pattern = r"(?<!\\),"

        # Split fields (handles quoted strings)
        # Splits on commas NOT inside quotes
        self.field_split_pattern = r',(?=(?:[^"]*"[^"]*")*[^"]*$)'

    def parse_line(self, line: str) -> ParsedPoint:
        """
        Parse a single line protocol string.

        Args:
            line: Line protocol string

        Returns:
            ParsedPoint with extracted components

        Raises:
            ParseError: If line is malformed

        Examples:
            "cpu,host=server1 usage=75.5 1609459200000000000"
            -> ParsedPoint(
                measurement="cpu",
                tags={"host": "server1"},
                fields={"usage": 75.5},
                timestamp=1609459200.0
            )
        """
        # TODO: Implement line protocol parsing
        # Steps:
        # 1. Split line into main components (measurement+tags, fields, timestamp)

        line_protocol_parts = re.split(
            self.split_protocol_pattern, line.strip(), maxsplit=2
        )
        if len(line_protocol_parts) < 2:
            raise ParseError("Line must have measurement/tags and fields", line=line)

        # 2. Parse measurement and tags
        measurement_and_tags_part = line_protocol_parts[0]
        fields_part = line_protocol_parts[1]
        timestamp_part = (
            line_protocol_parts[2] if len(line_protocol_parts) == 3 else None
        )

        # 3. Parse fields with type detection
        fields = self.parse_fields(fields_part)

        # 4. Parse timestamp if is None then let storage/write layer handle defaulting
        if timestamp_part:
            timestamp = self.parse_timestamp(timestamp_part)
        else:
            timestamp = None

        # 5. Handle escaping throughout
        measurement, tags = self.parse_measurement_and_tags(measurement_and_tags_part)

        # Hint: Use string methods and careful splitting
        # Handle edge cases: empty tags, multiple fields, escaping

        return ParsedPoint(
            measurement=measurement,
            tags=tags,
            fields=fields,
            timestamp=timestamp,
        )

    def parse_measurement_and_tags(
        self, measurement_part: str
    ) -> Tuple[str, Dict[str, str]]:
        """
        Parse measurement name and tag pairs.

        Args:
            measurement_part: "measurement,tag1=val1,tag2=val2"

        Returns:
            Tuple of (measurement_name, tags_dict)

        Requirements:
        - Handle escaped characters in measurement name
        - Parse all tag key-value pairs
        - Validate tag keys and values
        - Handle empty tag set (just measurement)

        Examples:
            "cpu,host=server1,region=us-west"
            -> ("cpu", {"host": "server1", "region": "us-west"})
        """
        # TODO: Split by comma and parse measurement + tags
        parts = re.split(self.tag_split_pattern, measurement_part)

        # TODO: Handle escaping in measurement name
        measurement = parts[0].strip()
        if not self.validate_measurement_name(measurement):
            raise ParseError(
                f"Invalid measurement: '{measurement}'", line=measurement_part
            )

        # TODO: Parse each tag key=value pair
        tags: Dict[str, str] = {}
        for tag_kv in parts[1:]:
            key_value = tag_kv.split("=", 1)
            # Validate key-value pair
            if len(key_value) != 2:
                raise ParseError("Invalid tag key-value pair", line=tag_kv)

            key = key_value[0].strip()
            if not self.validate_tag_key(key):
                raise ParseError(f"Invalid tag key: '{key}'")

            value = self.unescape_string(key_value[1].strip(), context="tag_value")

            tags[key] = value

        return measurement, tags

    def parse_fields(self, fields_part: str) -> Dict[str, Union[int, float, str, bool]]:
        """
        Parse field key-value pairs with type detection.

        Args:
            fields_part: "field1=value1,field2=value2"

        Returns:
            Dictionary with field names and typed values

        Type Detection Rules:
        - Integers: End with 'i' (e.g., "42i")
        - Floats: Numbers without 'i' (e.g., "3.14")
        - Strings: Quoted (e.g., '"hello"')
        - Booleans: true/false/t/f/True/False/TRUE/FALSE

        Examples:
            'cpu=75.5,count=42i,name="server",online=true'
            -> {"cpu": 75.5, "count": 42, "name": "server", "online": True}
        """
        fields: Dict[str, Union[int, float, str, bool]] = {}

        # TODO: Split by comma (careful with quoted strings!)
        # fields_part = fields_part.strip().split(",")
        fields_part = re.split(self.field_split_pattern, fields_part.strip())
        for field_kv in fields_part:
            field_kv = field_kv.strip()
            if not field_kv:
                continue

            key_value = field_kv.split("=", 1)
            # Validate key-value pair
            # the error occurs here when there is no '=' in field_kv
            # or when field_kv is empty
            if len(key_value) != 2:
                raise ParseError("Invalid field key-value pair", line=field_kv)

            # TODO: Parse each field=value pair
            key = key_value[0].strip()
            if not key:
                raise ParseError("Empty field key", line=field_kv)

            if not self.validate_field_key(key):
                raise ParseError(f"Invalid field key: '{key}'", line=field_kv)

            # TODO: Detect and convert field value types
            value_str = key_value[1].strip()
            if not value_str:
                raise ParseError(f"Empty field value for key '{key}'", line=field_kv)
            value = self.detect_field_type(value_str)

            # TODO: Handle escaping in string values
            if isinstance(value, str):
                value = self.unescape_string(value, context="field_value")

            fields[key] = value

        return fields

    def detect_field_type(self, value_str: str) -> Union[int, float, str, bool]:
        """
        Detect and convert field value type.

        Args:
            value_str: Raw value string from line protocol

        Returns:
            Converted value with correct Python type

        Type Rules:
        - "42i" -> 42 (integer)
        - "3.14" -> 3.14 (float)
        - '"hello"' -> "hello" (string, remove quotes)
        - "true" -> True (boolean, case insensitive)
        """
        # TODO: Implement type detection logic
        # Handle integer suffix 'i'
        if value_str.endswith("i"):
            return int(value_str[:-1])

        # Handle quoted strings
        if value_str.startswith('"') and value_str.endswith('"'):
            return str(value_str[1:-1])

        # Handle boolean values
        if value_str.lower() in ["true", "t"]:
            return True
        if value_str.lower() in ["false", "f"]:
            return False

        # Default to float for numbers
        return float(value_str)

    def parse_timestamp(self, timestamp_str: str) -> float:
        """
        Parse timestamp with precision detection.

        Args:
            timestamp_str: Timestamp string

        Returns:
            Unix timestamp as float (seconds)

        Precision Detection:
        - 10 digits: seconds (1609459200)
        - 13 digits: milliseconds (1609459200000)
        - 16 digits: microseconds (1609459200000000)
        - 19 digits: nanoseconds (1609459200000000000)

        Requirements:
        - Auto-detect precision by digit count
        - Convert all to seconds (float)
        - Handle invalid timestamps gracefully
        """
        # TODO: Detect precision by string length
        timestamp_str = timestamp_str.strip()
        length = len(timestamp_str)

        # TODO: Convert to seconds
        try:
            if length == 10:
                # Seconds
                seconds = float(timestamp_str)
            elif length == 13:
                # Milliseconds
                seconds = float(timestamp_str) / 1e3
            elif length == 16:
                # Microseconds
                seconds = float(timestamp_str) / 1e6
            elif length == 19:
                # Nanoseconds
                seconds = float(timestamp_str) / 1e9
            else:
                raise ParseError("Invalid timestamp length", line=timestamp_str)

        except ValueError as ex:
            raise ParseError("Invalid timestamp format", line=timestamp_str) from ex

        # TODO: Validate timestamp range
        # if timestamp is too far in future or negative or timestamp > current time
        # we don't allow timestamps higher than current time
        # This prevents future timestamps
        # or too far in past (e.g., before 1970)
        current_time = time.time()
        if seconds < 0:
            raise ParseError(f"Negative timestamp: {seconds}")
        if seconds > current_time + 86400:  # Allow 1 day in future
            raise ParseError(f"Timestamp too far in future: {seconds}")

        return seconds

    def unescape_string(self, escaped_str: str, context: str = "tag_value") -> str:
        """
        Unescape special characters.

        Args:
            escaped_str: String with escape sequences
            context: Where string is used ("tag_value", "field_value")

        Returns:
            Unescaped string

        Escape Rules by Context:
        - tag_value: Unescape \\, \\= \\  (comma, equals, space)
        - field_value: Unescape \\" \\\\ (quote, backslash)

        Examples:
            unescape_string(r"us\\ west", "tag_value") -> "us west"
            unescape_string(r'say \\"hi\\"', "field_value") -> 'say "hi"'
        Important:
            This function is ONLY for VALUES!
            Keys and measurement names should NOT be unescaped.
        """
        # TODO: Implement context-specific unescaping
        if context == "tag_value":
            # Tag values can have: comma, equals, space
            return (
                escaped_str.replace(r"\,", ",").replace(r"\=", "=").replace(r"\ ", " ")
            )
        elif context == "field_value":
            # String field values can have: quotes, backslashes
            return (
                escaped_str.replace(r"\\", chr(0))
                .replace(r"\"", '"')
                .replace(chr(0), "\\")
            )
        else:
            raise ValueError(
                f"Invalid context '{context}'. "
                "Use 'tag_value' or 'field_value' only."
            )

    def parse_batch(self, lines: List[str]) -> List[ParsedPoint]:
        """
        Parse multiple lines, handling errors gracefully.

        Args:
            lines: List of line protocol strings

        Returns:
            List of successfully parsed points

        Requirements:
        - Skip invalid lines with warning
        - Collect parse errors for debugging
        - Return as many valid points as possible
        - Log parsing statistics
        """
        parsed_points: List[ParsedPoint] = []

        # TODO: Parse each line individually
        for line in lines:
            try:
                point = self.parse_line(line)
            except ParseError as e:
                # TODO: Collect errors but don't fail completely
                print(f"Warning: Skipping invalid line: {e}")
                continue

            parsed_points.append(point)

        # TODO: Return list of successful parses
        return parsed_points

    def validate_measurement_name(self, measurement: str) -> bool:
        """
        Validate measurement name.

        Args:
            measurement: Measurement name to validate

        Returns:
            True if valid, False otherwise

        Rules:
        - Must not be empty
        - Should not start with underscore (reserved)
        - Can contain letters, numbers, underscores, hyphens
        - Case sensitive
        """
        # TODO: Implement validation rules
        if not measurement:
            return False

        if measurement.startswith("_"):
            return False

        # to make sure only valid characters are used
        if not self.measurement_pattern.match(measurement):
            return False

        return True

    def validate_tag_key(self, key: str) -> bool:
        """
        Validate tag key name.

        Similar rules to measurement names.
        """
        # TODO: Implement tag key validation
        if not key:
            return False

        if key.startswith("_"):
            return False

        if not self.tag_key_pattern.match(key):
            return False

        return True

    def validate_field_key(self, key: str) -> bool:
        """
        Validate tag key name.

        Similar rules to measurement names.
        """
        # TODO: Implement tag key validation
        if not key:
            return False

        if key.startswith("_"):
            return False

        if not self.field_key_pattern.match(key):
            return False

        return True
