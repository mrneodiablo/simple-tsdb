#!/usr/bin/env python3
"""
Day 10: Series Key Management
=============================

Problem: Give every unique (measurement + tag set) a stable, canonical identity
("series key") and a compact integer id, so the rest of the engine can refer to
series cheaply and count cardinality.

Learning Objectives:
- Build a canonical, order-independent series key from measurement + tags
- Round-trip: encode a series key AND parse it back to its parts
- Assign compact integer ids and maintain a two-way mapping
- Track cardinality globally and per-measurement
- Handle escaping so commas/equals in tag values don't break the format

Real-World Connection:
InfluxDB identifies each series by a key like
`cpu,host=server1,region=us-west`. Tags are sorted so the key is canonical
regardless of write order, and an internal series id keeps indexes small.
Series cardinality is THE capacity-planning metric for InfluxDB.
"""

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


def test_series_keys():
    """Test cases for series key management."""
    print("Testing Series Key Management...")

    mgr = SeriesManager()

    # Test 1: canonical key is order-independent
    k1 = mgr.make_series_key("cpu", {"host": "server1", "region": "us-west"})
    k2 = mgr.make_series_key("cpu", {"region": "us-west", "host": "server1"})
    assert k1 == k2 == "cpu,host=server1,region=us-west", f"got {k1!r}"
    print("✓ Test 1 passed: canonical, order-independent key")

    # Test 2: no-tag series
    assert mgr.make_series_key("uptime", {}) == "uptime"
    print("✓ Test 2 passed: measurement with no tags")

    # Test 3: round-trip parse
    measurement, tags = mgr.parse_series_key("cpu,host=server1,region=us-west")
    assert measurement == "cpu"
    assert tags == {"host": "server1", "region": "us-west"}
    print("✓ Test 3 passed: parse round-trip")

    # Test 4: escaping commas/equals in values
    weird = mgr.make_series_key("http", {"path": "/a,b=c"})
    m2, t2 = mgr.parse_series_key(weird)
    assert m2 == "http" and t2 == {"path": "/a,b=c"}, f"escape round-trip failed: {t2}"
    print("✓ Test 4 passed: escaping special characters")

    # Test 5: id assignment is stable and unique
    id_a = mgr.get_or_create_id("cpu", {"host": "server1"})
    id_b = mgr.get_or_create_id("cpu", {"host": "server2"})
    id_a_again = mgr.get_or_create_id("cpu", {"host": "server1"})
    assert id_a == id_a_again, "Same series must keep the same id"
    assert id_a != id_b, "Different series must get different ids"
    assert mgr.get_key(id_a) == "cpu,host=server1"
    assert mgr.get_id("cpu,host=server2") == id_b
    print("✓ Test 5 passed: stable, unique id mapping")

    # Test 6: cardinality tracking
    mgr.get_or_create_id("mem", {"host": "server1"})
    report = mgr.cardinality_report()
    assert report.total_series == mgr.cardinality()
    assert report.by_measurement["cpu"] == 2
    assert report.by_measurement["mem"] == 1
    print(f"✓ Test 6 passed: cardinality -> total={report.total_series}, "
          f"by_measurement={report.by_measurement}")

    # Test 7: enumerate a measurement's series
    cpu_series = mgr.series_for_measurement("cpu")
    assert set(cpu_series) == {"cpu,host=server1", "cpu,host=server2"}
    print("✓ Test 7 passed: series_for_measurement")

    print("\n🎉 All series key tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement _escape/_unescape and every SeriesManager method.
    2. Run: python day10_series_keys.py
    3. All 7 tests should pass.

    Success criteria:
    - keys are canonical (tag order doesn't matter) and reversible
    - special characters survive a make -> parse round-trip
    - ids are stable, unique, and cheap to look up both directions

    Next steps:
    - Day 11 persists these maps (and the Day 8/9 indexes) to disk.
    - Think about: why is an integer series id cheaper than the string key in
      every other index?
    """
    test_series_keys()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Canonical Keys
   - Sorting tags makes the key deterministic regardless of insertion order, so
     the SAME logical series always hashes/compares equal.

2. Escaping
   - Any delimiter-based format must escape its delimiters inside the data.
     Escape the escape char FIRST when encoding, and treat '\\' as "take next
     char literally" when decoding.

3. Series Ids
   - The string key is human-readable but expensive to repeat in every posting
     list. A compact integer id (stored once in a two-way map) shrinks every
     downstream index — tag index, time index, query results.

4. Cardinality
   - cardinality = number of distinct series = rows in this registry.
   - Per-measurement breakdown tells you WHICH measurement is exploding, which
     is the first question in any InfluxDB cardinality incident.

Connection to InfluxDB:
- Series key format here mirrors InfluxDB's `measurement,tagk=tagv,...`.
- InfluxDB assigns internal series ids and tracks cardinality per measurement;
  `SHOW SERIES CARDINALITY` is the production equivalent of cardinality_report.

Trade-offs:
- String keys: readable, debuggable, but large.
- Integer ids: compact and fast, but need the registry to translate back.
"""
