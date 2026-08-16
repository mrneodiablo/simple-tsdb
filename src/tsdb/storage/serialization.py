#!/usr/bin/env python3

import json
import time
from typing import Dict, List, Any, Optional
from enum import Enum
import hashlib


class FieldType(Enum):
    """Field types supported by time-series database."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"


class DataPoint:
    """
    Represents a single time-series data point.

    Structure:
    - measurement: Name of the measurement (e.g., "cpu", "http_request")
    - timestamp: Unix timestamp (float)
    - tags: Key-value pairs for indexing (all strings)
    - fields: Key-value pairs for actual data (typed)
    """

    def __init__(
        self,
        measurement: str,
        timestamp: float,
        tags: Dict[str, str],
        fields: Dict[str, Any],
    ):
        """Initialize data point with validation."""
        # TODO: Implement initialization with validation
        # we can use Pydantic or dataclasses for validation, but for simplicity, we'll do manual checks here
        # Requirements:
        # - measurement must be non-empty string
        if not measurement or not isinstance(measurement, str):
            raise ValueError("Measurement must be a non-empty string.")
        self.measurement = measurement

        # - timestamp must be positive number
        if not isinstance(timestamp, (int, float)) or timestamp < 0:
            raise ValueError("Timestamp must be a positive number.")
        self.timestamp = timestamp

        # - tags values must all be strings
        for k, v in tags.items():
            if not isinstance(v, str):
                raise ValueError(f"Tag value for '{k}' must be a string.")
        self.tags = tags

        # - fields must have at least one entry
        if not fields or not isinstance(fields, dict):
            raise ValueError("Fields must be a non-empty dictionary.")
        else:
            if len(fields) == 0:
                raise ValueError("Fields must contain at least one entry.")
        self.fields = fields

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert data point to dictionary for JSON serialization.

        Returns:
            Dictionary with structure:
            {
                "measurement": "cpu",
                "timestamp": 1672531200.123,
                "tags": {"host": "server1", "region": "us-west"},
                "fields": {
                    "cpu_usage": {"value": 75.5, "type": "float"},
                    "active_processes": {"value": 42, "type": "integer"},
                    "hostname": {"value": "web-01", "type": "string"},
                    "is_healthy": {"value": true, "type": "boolean"}
                }
            }

        Requirements:
        - Preserve field types explicitly
        - Include type information for each field
        - Handle all supported field types
        """
        # TODO: Convert to dictionary with type preservation
        # because data type of field values can be int, float, str, bool
        # we need to create a structure that includes both value and type
        field_dict = {}
        for field_name, value in self.fields.items():
            if isinstance(value, bool):
                field_type = FieldType.BOOLEAN.value
            elif isinstance(value, int):
                field_type = FieldType.INTEGER.value
            elif isinstance(value, float):
                field_type = FieldType.FLOAT.value
            elif isinstance(value, str):
                field_type = FieldType.STRING.value
            else:
                raise ValueError(
                    f"Unsupported field type for '{field_name}': {type(value)}"
                )

            field_dict[field_name] = {"value": value, "type": field_type}

        return {
            "measurement": self.measurement,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "fields": field_dict,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataPoint":
        """
        Create data point from dictionary (JSON deserialization).

        Args:
            data: Dictionary from JSON with type information

        Returns:
            DataPoint instance with correct types

        Requirements:
        - Restore original field types from type information
        - Validate data structure
        - Handle missing or invalid type information
        """
        # TODO: Reconstruct DataPoint from dictionary
        measurement = data["measurement"]
        timestamp = data["timestamp"]
        tags = data["tags"]
        fields_data = data["fields"]

        # TODO: Convert field values back to correct types
        fields = {}
        for field_name, field_info in fields_data.items():
            value = field_info["value"]
            field_type = field_info["type"]
            # TODO: Convert value to correct type based on field_type
            # since boolean is subclass of int in Python, we need to check for boolean type first
            if field_type == FieldType.BOOLEAN.value:
                fields[field_name] = bool(value)
            elif field_type == FieldType.INTEGER.value:
                fields[field_name] = int(value)
            elif field_type == FieldType.FLOAT.value:
                fields[field_name] = float(value)
            elif field_type == FieldType.STRING.value:
                fields[field_name] = str(value)
            else:
                raise ValueError(
                    f"Unsupported field type for '{field_name}': {field_type}"
                )
        return cls(measurement, timestamp, tags, fields)

    def get_field_type(self, field_name: str) -> Optional[FieldType]:
        """
        Get the type of a specific field.

        Args:
            field_name: Name of the field

        Returns:
            FieldType enum value or None if field doesn't exist
        """
        # TODO: Determine and return field type
        value = self.fields.get(field_name)
        if value is None:
            return None

        if isinstance(value, bool):
            return FieldType.BOOLEAN
        elif isinstance(value, int):
            return FieldType.INTEGER
        elif isinstance(value, float):
            return FieldType.FLOAT
        elif isinstance(value, str):
            return FieldType.STRING
        else:
            return None

    def to_line_protocol(self) -> str:
        """
        Convert data point to InfluxDB line protocol format.

        Returns:
            String in format: "measurement,tag1=val1,tag2=val2 field1=val1,field2=val2 timestamp"

        Requirements:
        - Escape special characters in tags and field names
        - Format field values according to type (integers with 'i' suffix)
        - Handle empty tag sets
        - Use nanosecond precision for timestamp

        Example:
            "cpu,host=server1,region=us-west cpu_usage=75.5,processes=42i 1672531200000000000"
        """
        # TODO: Generate line protocol string
        line_protocol_string = self.measurement

        # Format tags
        tag_parts = []
        for k, v in self.tags.items():

            # TODO: Escape special characters in tag keys and values
            # if k or v contain spaces, commas, or equal signs, we need to escape them with \
            if any(c in k for c in " ,="):
                k = k.replace(" ", r"\ ").replace(",", r"\,").replace("=", r"\=")

            if any(c in v for c in " ,="):
                v = v.replace(" ", r"\ ").replace(",", r"\,").replace("=", r"\=")

            tag_parts.append(f"{k}={v}")
        tag_str = ",".join(tag_parts)
        if tag_str:
            line_protocol_string += f",{tag_str}"

        # TODO: Format field values with type indicators
        field_parts = []
        for k, v in self.fields.items():
            # TODO: Escape special characters in field keys
            if any(c in k for c in " ,="):
                k = k.replace(" ", r"\ ").replace(",", r"\,").replace("=", r"\=")

            if isinstance(v, bool):
                field_parts.append(f"{k}={str(v).lower()}")
            elif isinstance(v, int):
                field_parts.append(f"{k}={v}i")
            elif isinstance(v, float):
                field_parts.append(f"{k}={v}")
            elif isinstance(v, str):
                # TODO: Escape special characters in field string value
                if any(c in v for c in " ,="):
                    v = v.replace(" ", r"\ ").replace(",", r"\,").replace("=", r"\=")
                field_parts.append(f'{k}="{v}"')
            else:
                raise ValueError(f"Unsupported field type for '{k}': {type(v)}")
        fields_str = ",".join(field_parts)

        if fields_str:
            line_protocol_string += f" {fields_str}"

        # Format timestamp in nanoseconds
        timestamp_ns = int(self.timestamp * 1e9)
        line_protocol_string += f" {timestamp_ns}"

        return line_protocol_string


class TimeSeriesSerializer:
    """
    Handles serialization/deserialization of time-series data.

    Features:
    - Batch operations for efficiency
    - Compression for repeated tag values
    - Schema evolution support
    - Error recovery
    """

    def __init__(self):
        """Initialize serializer with configuration."""
        # TODO: Initialize configuration
        # Consider: compression settings, schema version, etc.
        self.version = None
        self.count = 0
        self.serialized_at = None
        self.data_points = None

    def serialize_batch(self, data_points: List[DataPoint]) -> str:
        """
        Serialize a batch of data points to JSON string.

        Args:
            data_points: List of DataPoint instances

        Returns:
            JSON string representing the batch

        Requirements:
        - Include metadata (version, timestamp, count)
        - Optimize for repeated tag values
        - Handle empty batches
        - Include checksum for integrity

        Format:
        {
            "version": "1.0",
            "serialized_at": 1672531200.123,
            "count": 3,
            "checksum": "abc123",
            "data_points": [...]
        }
        """
        # TODO: Create batch structure with metadata
        self.version = "1.0"
        self.serialized_at = time.time()
        self.count = len(data_points)

        # TODO: Serialize all data points
        self.data_points = [dp.to_dict() for dp in data_points]
        batch_dict = {
            "version": self.version,
            "serialized_at": self.serialized_at,
            "count": self.count,
            "data_points": self.data_points,
        }
        # TODO: Calculate checksum
        batch_json = json.dumps(batch_dict)
        batch_dict["checksum"] = self.calculate_checksum(batch_json)

        return json.dumps(batch_dict)

    def deserialize_batch(self, json_str: str) -> List[DataPoint]:
        """
        Deserialize JSON string to list of data points.

        Args:
            json_str: JSON string from serialize_batch

        Returns:
            List of DataPoint instances

        Requirements:
        - Validate version compatibility
        - Verify checksum
        - Handle corrupted data gracefully
        - Support partial recovery
        """
        # TODO: Parse JSON and validate structure
        data_points = []
        batch_dict = json.loads(json_str)
        version = batch_dict.get("version")
        if version != "1.0":
            raise ValueError(f"Unsupported version: {version}")

        data_points_data = batch_dict.get("data_points", [])

        # TODO: Verify checksum
        checksum = batch_dict.get("checksum")

        # why we need to recalculate checksum here?
        # since checksum is calculated from json without checksum field
        # so we need to remove checksum field before recalculating
        temp_dict = batch_dict.copy()
        temp_dict.pop("checksum", None)
        temp_json = json.dumps(temp_dict)
        recalculated_checksum = self.calculate_checksum(temp_json)
        if checksum != recalculated_checksum:
            raise ValueError("Checksum mismatch - data may be corrupted")

        # TODO: Deserialize each data point
        for dp_data in data_points_data:
            data_points.append(DataPoint.from_dict(dp_data))

        return data_points

    def compress_tags(self, data_points: List[DataPoint]) -> Dict[str, Any]:
        """
        Compress repeated tag values in a batch.
        Reduce storage by creating a tag dictionary.
        The main idea is like using references instead of repeating same tags.


        Args:
            data_points: List of data points

        Returns:
            Compressed representation with tag dictionary

        Optimization:
        Instead of repeating tags in each point:
        [
            {"tags": {"host": "server1", "region": "us-west"}, ...},
            {"tags": {"host": "server1", "region": "us-west"}, ...}
        ]

        Use tag references:
        {
            "tag_dictionary": {
                "0": {"host": "server1", "region": "us-west"},
                "1": {"host": "server2", "region": "us-east"}
            },
            "points": [
                {"tag_ref": "0", "fields": ...},
                {"tag_ref": "0", "fields": ...}
            ]
        }

        the compress_tags is optional method to implement compression logic
        and we will not use it by default in serialize_batch
        we can call it separately if needed or have a flag in serialize_batch to enable it
        """

        # TODO: Find unique tag combinations
        # to find unique tag combinations,
        # we can use frozenset to represent tags as immutable set of key-value pairs in tag_to_id
        # example tag_to_id = {frozenset({("host", "server1"), ("region", "us-west")}): "0"}
        tag_to_id = {}

        tag_dict = {}

        compressed_points = []
        tag_id_counter = 0  # monotonically increasing ID for each unique tag set

        for dp in data_points:
            # Convert tags to immutable frozenset
            tag_key = frozenset(dp.tags.items())

            # example tag_dict = {"0": {"host": "server1", "region": "us-west"}}
            if tag_key not in tag_to_id:
                # Assign ID if new tag combination
                tag_id = str(tag_id_counter)
                tag_id_counter += 1

                tag_to_id[tag_key] = tag_id

                # TODO: Create tag dictionary
                # tag_dict = {"tag_id": {"host": "server1", "region": "us-west"}}
                tag_dict[tag_id] = dp.tags

            # Build compressed point
            compressed_points.append(
                {
                    # TODO: Replace tags with references
                    "tag_ref": tag_to_id[tag_key],
                    "measurement": dp.measurement,
                    "timestamp": dp.timestamp,
                    "fields": dp.fields,
                }
            )

        return {"tag_dictionary": tag_dict, "points": compressed_points}

    def calculate_checksum(self, data: str) -> str:
        """
        Calculate simple checksum for data integrity.

        Args:
            data: String data to checksum

        Returns:
            Hexadecimal checksum string

        Requirements:
        - Fast calculation
        - Good error detection
        - Consistent across runs
        """
        # TODO: Calculate checksum (consider MD5 or CRC32 or similar)
        # MD5 as AI memtion it much slower than CRC32, but i's more familiar with MD5 let's use it here
        checksum = hashlib.md5(data.encode("utf-8")).hexdigest()
        return checksum
