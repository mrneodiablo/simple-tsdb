#!/usr/bin/env python3

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class CardinalityReport:
    """Cardinality breakdown for capacity planning."""

    total_series: int = 0
    by_measurement: Dict[str, int] = field(default_factory=dict)

    @property
    def measurement_count(self) -> int:
        return len(self.by_measurement)


def _escape(value: str) -> str:
    """
    Escape the structural characters used by the series-key format.

    We use ',' between tags and '=' between key and value, so those plus the
    escape char itself must be escaped inside measurement names and tag values.
    """
    # TODO: Escape backslash first, then ',' and '=' (order matters!)
    #       e.g. "\\" -> "\\\\", "," -> "\\,", "=" -> "\\="
    value = value.replace("\\", "\\\\")
    value = value.replace(",", "\\,")
    value = value.replace("=", "\\=")
    return value


def _unescape(value: str) -> str:
    """Reverse of _escape."""
    # TODO: Walk the string; when you see '\', take the next char literally
    result = []
    i = 0
    while i < len(value):
        if value[i] == '\\':
            i += 1  # Skip the escape char
            if i < len(value):
                result.append(value[i])  # Take the next char literally
        else:
            result.append(value[i])
        i += 1
    return ''.join(result)


class SeriesManager:
    """
    Canonical series keys + integer id assignment + cardinality tracking.

    Series key format (tags sorted by key):
        measurement[,k1=v1][,k2=v2]...
    Example:
        make_series_key("cpu", {"region": "us-west", "host": "server1"})
        -> "cpu,host=server1,region=us-west"
    """

    def __init__(self) -> None:
        self._key_to_id: Dict[str, int] = {}
        self._id_to_key: Dict[int, str] = {}
        self._measurement_of: Dict[int, str] = {}
        self._next_id: int = 0

    # ----------------------------------------------------------- key encoding
    def make_series_key(self, measurement: str, tags: Dict[str, str]) -> str:
        """
        Build the canonical series key.

        Requirements:
        - tags sorted by key so write order doesn't matter
        - measurement, tag keys and tag values all escaped
        - measurement with no tags -> just the (escaped) measurement
        """
        # TODO: Validate measurement is a non-empty string
        if not isinstance(measurement, str) or not measurement:
            raise ValueError("Measurement must be a non-empty string")
        
        # TODO: Sort tags by key, escape each part, join "k=v" with commas
        escaped_measurement = _escape(measurement)

        # TODO: Prefix with the escaped measurement
        escaped_tags = [f"{_escape(k)}={_escape(v)}" for k, v in sorted(tags.items())]
        if escaped_tags:
            return f"{escaped_measurement}," + ",".join(escaped_tags)
        else:
            return escaped_measurement
        
    def parse_series_key(self, series_key: str) -> Tuple[str, Dict[str, str]]:
        """
        Inverse of make_series_key: return (measurement, tags).

        Must respect escaping — a '\\,' inside a value is NOT a separator.
        """
        # TODO: Split on UNescaped commas (watch for the escape char)
        if not series_key:
            raise ValueError("Series key must be a non-empty string")
        
        parts = []
        current = []
        escape = False
        for char in series_key:
            if escape:
                current.append(char)
                escape = False
            elif char == '\\':
                escape = True
            elif char == ',':
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)
        parts.append(''.join(current))  # Add the last part

        
        parts = [_unescape(part) for part in parts]
        # TODO: First token = measurement; the rest are k=v (split on first
        #       UNescaped '=')
        measurement = parts[0]
        tags = {}
        # TODO: Unescape every piece
        for part in parts[1:]:
            k, v = part.split("=", 1)
            tags[k] = v
        return measurement, tags

    # ------------------------------------------------------------ id registry
    def get_or_create_id(self, measurement: str, tags: Dict[str, str]) -> int:
        """
        Return the series id for (measurement, tags), assigning a new one the
        first time this series is seen. Stable across calls.
        """
        # TODO: Build the key, look it up; if absent assign self._next_id,
        #       update all three maps, increment, and remember the measurement
        series_key = self.make_series_key(measurement, tags)
        if series_key in self._key_to_id:
            return self._key_to_id[series_key]
        series_id = self._next_id
        self._key_to_id[series_key] = series_id
        self._id_to_key[series_id] = series_key
        self._measurement_of[series_id] = measurement
        self._next_id += 1
        return series_id

    def get_id(self, series_key: str) -> Optional[int]:
        """Return the id for an existing series key, or None."""
        # TODO
        return self._key_to_id.get(series_key, None)

    def get_key(self, series_id: int) -> Optional[str]:
        """Return the series key for an id, or None."""
        # TODO
        return self._id_to_key.get(series_id, None)

    # ----------------------------------------------------------- cardinality
    def cardinality(self) -> int:
        """Total number of distinct series registered."""
        # TODO
        return len(self._key_to_id)

    def cardinality_report(self) -> CardinalityReport:
        """Full breakdown: total + per-measurement counts."""
        # TODO: Tally series ids grouped by their measurement
        report = CardinalityReport()
        report.total_series = self.cardinality()
        for series_id in self._id_to_key:
            measurement = self._measurement_of[series_id]
            report.by_measurement[measurement] = report.by_measurement.get(measurement, 0) + 1
        return report


    def series_for_measurement(self, measurement: str) -> List[str]:
        """All series keys belonging to a measurement (sorted)."""
        series_keys = [self._id_to_key[series_id] for series_id in self._id_to_key
                       if self._measurement_of[series_id] == measurement]
        return sorted(series_keys)

