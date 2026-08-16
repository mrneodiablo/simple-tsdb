#!/usr/bin/env python3

import struct
import time
import json
import zlib
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class CompressionType(Enum):
    """Supported compression algorithms."""

    NONE = "none"
    DELTA_ENCODING = "delta"
    RUN_LENGTH = "rle"
    GORILLA_FLOAT = "gorilla"
    DICTIONARY = "dict"
    GZIP = "gzip"
    MIXED = "mixed"  # Use best algorithm per field


@dataclass
class CompressionStats:
    """Statistics from compression operation."""

    original_bytes: int = 0
    compressed_bytes: int = 0
    compression_time: float = 0.0
    decompression_time: float = 0.0
    algorithm_used: str = "none"

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (original/compressed)."""
        return (
            self.original_bytes / self.compressed_bytes
            if self.compressed_bytes > 0
            else 1.0
        )

    @property
    def space_savings(self) -> float:
        """Calculate space savings percentage."""
        return (
            (1 - self.compressed_bytes / self.original_bytes) * 100
            if self.original_bytes > 0
            else 0.0
        )


class DeltaEncoder:
    """
    Delta encoding for timestamps and monotonic sequences.

    Delta encoding stores the difference between consecutive values instead
    of the absolute values. Very effective for timestamps.

    Example:
    Original: [1672531200, 1672531201, 1672531202, 1672531203]
    Delta:    [1672531200, 1, 1, 1]  # Much smaller numbers!
    """

    def encode_timestamps(self, timestamps: List[float]) -> bytes:
        """
        Encode list of timestamps using delta compression.

        Args:
            timestamps: List of timestamps (sorted)

        Returns:
            Compressed bytes

        Format:
        - First timestamp: 8 bytes (double)
        - Each delta: variable-length integer encoding
        """
        if not timestamps:
            return b""

        # Store the first timestamp as-is, then encode millisecond deltas.
        # Millisecond precision is enough for this exercise and keeps deltas small.
        encoded = bytearray(struct.pack("<d", float(timestamps[0])))
        previous_ms = int(round(float(timestamps[0]) * 1000.0))

        # TODO: Use variable-length encoding for small deltas
        def _encode_varint(value: int) -> bytes:
            out = bytearray()
            while True:
                to_write = value & 0x7F
                value >>= 7
                if value:
                    out.append(to_write | 0x80)
                else:
                    out.append(to_write)
                    break
            return bytes(out)

        # TODO: Implement delta encoding for timestamps
        for ts in timestamps[1:]:
            current_ms = int(round(float(ts) * 1000.0))
            delta = current_ms - previous_ms

            # TODO: Handle negative deltas (out-of-order timestamps)
            # ZigZag transforms signed integers to unsigned so small negative
            # deltas also encode compactly.
            zigzag_delta = (delta << 1) ^ (delta >> 63)
            encoded.extend(_encode_varint(zigzag_delta))
            previous_ms = current_ms

        return bytes(encoded)

    def decode_timestamps(self, data: bytes) -> List[float]:
        """
        Decode delta-encoded timestamps.

        Args:
            data: Compressed timestamp data

        Returns:
            List of original timestamps
        """
        if not data:
            return []

        if len(data) < 8:
            raise ValueError("Invalid delta timestamp payload: missing first timestamp")

        # TODO: Decode first timestamp
        first_timestamp = struct.unpack("<d", data[:8])[0]
        timestamps = [first_timestamp]
        previous_ms = int(round(first_timestamp * 1000.0))
        offset = 8

        # TODO: Read and apply deltas to reconstruct original values
        while offset < len(data):
            # Decode one unsigned varint
            zigzag_delta = 0
            shift = 0

            while True:
                if offset >= len(data):
                    raise ValueError(
                        "Invalid delta timestamp payload: truncated varint"
                    )

                byte = data[offset]
                offset += 1

                zigzag_delta |= (byte & 0x7F) << shift  # lấy 7 bit giá trị
                if (byte & 0x80) == 0:  # bit 7 = 0 → xong
                    break

                shift += 7  # bit 7 = 1 → dịch tiếp 7 bit
                if shift > 63:
                    raise ValueError(
                        "Invalid delta timestamp payload: varint too large"
                    )

            # ZigZag decode back to signed delta
            delta = (zigzag_delta >> 1) ^ -(zigzag_delta & 1)
            previous_ms += delta
            timestamps.append(previous_ms / 1000.0)

        return timestamps

    def encode_integers(self, values: List[int]) -> bytes:
        """
        Encode list of integers using delta compression.

        Args:
            values: List of integer values

        Returns:
            Compressed bytes

        Optimizations:
        - Use variable-length encoding for deltas
        - Handle different delta ranges efficiently
        - Optimize for common patterns (constant deltas)
        """
        # TODO: Calculate deltas between consecutive values
        # TODO: Use variable-length encoding for deltas
        # TODO: Handle different integer sizes optimally
        if not values:
            return b""

        def _encode_varint(value: int) -> bytes:
            out = bytearray()
            while True:
                to_write = value & 0x7F
                value >>= 7
                if value:
                    out.append(to_write | 0x80)
                else:
                    out.append(to_write)
                    break
            return bytes(out)

        def _zigzag_encode(value: int) -> int:
            # Generic ZigZag for Python ints (including large negatives).
            shift_bits = value.bit_length() or 1
            return (value << 1) ^ (value >> shift_bits)

        encoded = bytearray()

        first_value = values[0]
        if not isinstance(first_value, int):
            raise TypeError("values must contain only integers")

        # Encode first value directly so decoding can reconstruct exact sequence.
        encoded.extend(_encode_varint(_zigzag_encode(first_value)))
        previous_value = first_value

        for current_value in values[1:]:
            if not isinstance(current_value, int):
                raise TypeError("values must contain only integers")

            delta = current_value - previous_value
            encoded.extend(_encode_varint(_zigzag_encode(delta)))
            previous_value = current_value

        return bytes(encoded)

    def decode_integers(self, data: bytes) -> List[int]:
        """Decode delta-encoded integers."""
        # TODO: Implement decoding logic matching encode_integers
        if not data:
            return []

        def _decode_varint(payload: bytes, offset: int) -> Tuple[int, int]:
            value = 0
            shift = 0

            while True:
                if offset >= len(payload):
                    raise ValueError("Invalid delta integer payload: truncated varint")

                byte = payload[offset]
                offset += 1

                value |= (byte & 0x7F) << shift
                if (byte & 0x80) == 0:
                    break

                shift += 7
                if shift > 63:
                    raise ValueError("Invalid delta integer payload: varint too large")

            return value, offset

        def _zigzag_decode(value: int) -> int:
            return (value >> 1) ^ -(value & 1)

        offset = 0

        # First value is encoded directly (not as delta)
        first_encoded, offset = _decode_varint(data, offset)
        first_value = _zigzag_decode(first_encoded)
        decoded_values = [first_value]
        previous_value = first_value

        # Remaining values are encoded as deltas
        while offset < len(data):
            delta_encoded, offset = _decode_varint(data, offset)
            delta = _zigzag_decode(delta_encoded)
            current_value = previous_value + delta
            decoded_values.append(current_value)
            previous_value = current_value

        return decoded_values

    def encode_variable_int(self, value: int) -> bytes:
        """
        Encode integer using variable-length encoding.

        Small integers use fewer bytes:
        - 0-127: 1 byte
        - 128-16383: 2 bytes
        - etc.
        """
        # TODO: Implement variable-length integer encoding
        # Similar to Protocol Buffers varint encoding
        if not isinstance(value, int):
            raise TypeError("value must be an integer")
        if value < 0:
            raise ValueError("encode_variable_int expects a non-negative integer")

        encoded = bytearray()
        while True:
            to_write = value & 0x7F
            value >>= 7
            if value:
                encoded.append(to_write | 0x80)
            else:
                encoded.append(to_write)
                break

        return bytes(encoded)

    def decode_variable_int(self, data: bytes, offset: int) -> Tuple[int, int]:
        """
        Decode variable-length integer.

        Returns:
            Tuple of (decoded_value, bytes_consumed)
        """
        # TODO: Implement variable-length integer decoding
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes-like")
        if not isinstance(offset, int):
            raise TypeError("offset must be an integer")
        if offset < 0 or offset >= len(data):
            raise ValueError("offset out of range")

        value = 0
        shift = 0
        start_offset = offset

        while True:
            if offset >= len(data):
                raise ValueError("Invalid varint payload: truncated value")

            byte = data[offset]
            offset += 1

            value |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break

            shift += 7
            if shift > 63:
                raise ValueError("Invalid varint payload: value too large")

        return value, (offset - start_offset)


class RunLengthEncoder:
    """
    Run-length encoding for repetitive data.

    RLE compresses sequences of identical values by storing
    the value once plus a count.

    Example:
    Original: [100, 100, 100, 100, 200, 200, 300]
    RLE:      [(100, 4), (200, 2), (300, 1)]
    """

    def encode_values(self, values: List[Any]) -> bytes:
        """
        Encode values using run-length encoding.

        Args:
            values: List of values (any comparable type)

        Returns:
            Compressed bytes

        Format for each run:
        - Value: JSON-encoded value
        - Count: variable-length integer
        """
        # Encode each run as (count, value, null-terminator) so decode_values can
        # recover the value boundary via the trailing \x00.
        if not values:
            return b""

        encoded = bytearray()
        current_value = values[0]
        count = 1
        encode_variable = DeltaEncoder().encode_variable_int  # Reuse variable int encoding

        def flush_run(value: Any, run_count: int) -> None:
            encoded.extend(encode_variable(run_count))
            encoded.extend(str(value).encode("utf-8"))
            encoded.append(0)  # null terminator (decode reads value up to \x00)

        for value in values[1:]:
            # Find runs of identical values.
            if value == current_value:
                count += 1
            else:
                flush_run(current_value, count)
                current_value = value
                count = 1
        flush_run(current_value, count)
        return bytes(encoded)

    def decode_values(self, data: bytes) -> List[Any]:
        """
        Decode run-length encoded values.

        Args:
            data: Compressed RLE data

        Returns:
            List of original values
        """
        # TODO: Decode runs and expand back to original values
        if not data:
            return []
        decoded = []
        offset = 0
        decode_variable = DeltaEncoder().decode_variable_int  # Reuse variable int decoding
        while offset < len(data):
            count, bytes_consumed = decode_variable(data, offset)
            offset += bytes_consumed
            # TODO: Read the value (assume UTF-8 string for simplicity)
            end_of_value = data.find(b'\x00', offset)  # Null-terminated
            if end_of_value == -1:
                raise ValueError("Invalid RLE payload: missing null terminator for value")
            value = data[offset:end_of_value].decode('utf-8')
            offset = end_of_value + 1
            decoded.extend([value] * count)
        return decoded

    def analyze_runs(self, values: List[Any]) -> Dict[str, Any]:
        """
        Analyze data to determine RLE effectiveness.

        Returns statistics about run lengths and compression potential.
        """
        # TODO: Calculate run length statistics
        # TODO: Estimate compression ratio
        # TODO: Determine if RLE would be beneficial
        if not values:
            return {
                "total_values": 0,
                "unique_values": 0,
                "total_runs": 0,
                "average_run_length": 0.0,
                "max_run_length": 0,
                "min_run_length": 0,
                "estimated_ratio": 1.0,
                "rle_beneficial": False,
            }

        runs: List[int] = []
        current_run = 1

        for i in range(1, len(values)):
            if values[i] == values[i - 1]:
                current_run += 1
            else:
                runs.append(current_run)
                current_run = 1
        runs.append(current_run)

        total_values = len(values)
        total_runs = len(runs)
        average_run_length = total_values / total_runs if total_runs > 0 else 0.0
        max_run_length = max(runs)
        min_run_length = min(runs)
        unique_values = len(set(values))

        # Rough estimate: original stores each value once, RLE stores one value
        # per run plus one count per run. Works well enough for decision guidance.
        estimated_ratio = (total_values / (2 * total_runs)) if total_runs > 0 else 1.0

        # If we don't reduce the number of logical entries meaningfully, skip RLE.
        rle_beneficial = estimated_ratio > 1.1

        return {
            "total_values": total_values,
            "unique_values": unique_values,
            "total_runs": total_runs,
            "average_run_length": average_run_length,
            "max_run_length": max_run_length,
            "min_run_length": min_run_length,
            "estimated_ratio": estimated_ratio,
            "rle_beneficial": rle_beneficial,
        }


class GorillaCompressor:
    """
    Gorilla compression for floating-point values.

    Gorilla compression (from Facebook's Gorilla paper) achieves excellent
    compression for time-series floats by XOR-ing consecutive values and
    storing only the differing bits.

    Simplified version - real Gorilla is more complex.
    """

    def encode_floats(self, values: List[float]) -> bytes:
        """
        Encode floats using simplified Gorilla compression.

        Args:
            values: List of float values

        Returns:
            Compressed bytes

        Algorithm:
        1. XOR each value with previous value
        2. Find leading and trailing zeros in XOR result
        3. Store only the significant bits
        """
        # TODO: Implement simplified Gorilla compression
        # TODO: XOR consecutive float values
        # TODO: Store only differing bits efficiently
        if not values:
            return b""

        def _encode_varint(value: int) -> bytes:
            out = bytearray()
            while True:
                to_write = value & 0x7F
                value >>= 7
                if value:
                    out.append(to_write | 0x80)
                else:
                    out.append(to_write)
                    break
            return bytes(out)

        encoded = bytearray()

        # Write number of values for deterministic decode boundaries.
        encoded.extend(struct.pack("<I", len(values)))

        # Write the first value in full (64-bit IEEE754).
        first_bits = self.float_to_bits(values[0])
        encoded.extend(struct.pack("<Q", first_bits))

        previous_bits = first_bits
        for value in values[1:]:
            current_bits = self.float_to_bits(value)
            xor_value = current_bits ^ previous_bits

            # XOR tends to be small when values change gradually, so varint helps.
            encoded.extend(_encode_varint(xor_value))
            previous_bits = current_bits

        return bytes(encoded)

    def decode_floats(self, data: bytes) -> List[float]:
        """Decode Gorilla-compressed floats."""
        if not data:
            return []

        # Need count (4 bytes) + first value bits (8 bytes).
        if len(data) < 12:
            raise ValueError("Invalid Gorilla payload: missing header")

        value_count = struct.unpack("<I", data[:4])[0]
        if value_count == 0:
            return []

        first_bits = struct.unpack("<Q", data[4:12])[0]
        decoded_values = [self.bits_to_float(first_bits)]
        previous_bits = first_bits
        offset = 12

        def _decode_varint(payload: bytes, start: int) -> Tuple[int, int]:
            value = 0
            shift = 0
            current = start

            while True:
                if current >= len(payload):
                    raise ValueError("Invalid Gorilla payload: truncated varint")

                byte = payload[current]
                current += 1

                value |= (byte & 0x7F) << shift
                if (byte & 0x80) == 0:
                    break

                shift += 7
                if shift > 63:
                    raise ValueError("Invalid Gorilla payload: varint too large")

            return value, current

        while len(decoded_values) < value_count:
            xor_value, offset = _decode_varint(data, offset)
            current_bits = previous_bits ^ xor_value
            decoded_values.append(self.bits_to_float(current_bits))
            previous_bits = current_bits

        # Reject extra trailing bytes to surface format mismatch early.
        if offset != len(data):
            raise ValueError("Invalid Gorilla payload: trailing bytes")

        return decoded_values

    def float_to_bits(self, value: float) -> int:
        """Convert float to 64-bit integer representation."""
        # TODO: Use struct to convert float to bits
        return struct.unpack("<Q", struct.pack("<d", float(value)))[0]

    def bits_to_float(self, bits: int) -> float:
        """Convert 64-bit integer back to float."""
        # TODO: Use struct to convert bits back to float
        return struct.unpack("<d", struct.pack("<Q", bits))[0]


class DictionaryCompressor:
    """
    Dictionary compression for string fields with limited vocabulary.

    Replaces repeated strings with shorter dictionary references.
    Very effective for tag values with limited cardinality.
    """

    def __init__(self):
        """Initialize empty dictionary."""
        # string -> index (built during encode)
        self._string_to_index: Dict[str, int] = {}
        # index -> string (reverse mapping for decode)
        self._index_to_string: Dict[int, str] = {}

    def encode_strings(self, strings: List[str]) -> Tuple[bytes, Dict[int, str]]:
        """
        Encode strings using dictionary compression.

        Args:
            strings: List of string values

        Returns:
            Tuple of (compressed_data, dictionary)
        """
        self._string_to_index = {}
        self._index_to_string = {}

        encode_varint = DeltaEncoder().encode_variable_int
        encoded = bytearray()

        for s in strings:
            if s not in self._string_to_index:
                idx = len(self._string_to_index)
                self._string_to_index[s] = idx
                self._index_to_string[idx] = s
            encoded.extend(encode_varint(self._string_to_index[s]))

        return bytes(encoded), dict(self._index_to_string)

    def decode_strings(self, data: bytes, dictionary: Dict[int, str]) -> List[str]:
        """
        Decode dictionary-compressed strings.

        Args:
            data: Compressed string indices
            dictionary: String dictionary

        Returns:
            List of original strings
        """
        if not data:
            return []

        decode_varint = DeltaEncoder().decode_variable_int
        decoded = []
        offset = 0

        while offset < len(data):
            idx, consumed = decode_varint(data, offset)
            offset += consumed
            if idx not in dictionary:
                raise ValueError(f"Invalid dictionary index: {idx}")
            decoded.append(dictionary[idx])

        return decoded


class TimeSeriesCompressor:
    """
    Main compression interface that chooses optimal algorithms for different data types.

    Features:
    - Automatic algorithm selection based on data characteristics
    - Mixed compression (different algorithms for different fields)
    - Compression statistics and profiling
    - Fallback to general-purpose compression (gzip)
    """

    def __init__(self):
        """Initialize compressor with all algorithms."""
        self.delta = DeltaEncoder()
        self.rle = RunLengthEncoder()
        self.gorilla = GorillaCompressor()
        self.dictionary = DictionaryCompressor()

    def compress_data_points(
        self, data_points: List[Dict[str, Any]]
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress list of time-series data points.

        Args:
            data_points: List of data points

        Returns:
            Tuple of (compressed_data, compression_metadata)

        Strategy: serialize the points to JSON and apply general-purpose (zlib)
        compression as a robust, exactly-reversible container. The per-column
        algorithms (delta/RLE/Gorilla/dictionary) are exercised and compared in
        benchmark_algorithms(); this container guarantees a correct round-trip.
        """
        raw = json.dumps(data_points, sort_keys=True).encode("utf-8")
        compressed = zlib.compress(raw, level=9)
        metadata = {
            "codec": "zlib+json",
            "count": len(data_points),
            "original_bytes": len(raw),
        }
        return compressed, metadata

    def decompress_data_points(
        self, compressed_data: bytes, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Decompress data points using metadata.

        Args:
            compressed_data: Compressed data bytes
            metadata: Compression metadata

        Returns:
            List of original data points
        """
        if not compressed_data:
            return []
        codec = metadata.get("codec", "zlib+json")
        if codec != "zlib+json":
            raise ValueError(f"unknown codec: {codec}")
        raw = zlib.decompress(compressed_data)
        return json.loads(raw.decode("utf-8"))

    def analyze_compression_potential(
        self, data_points: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze data to predict compression ratios for different algorithms.

        Returns analysis of which algorithms would work best.
        """
        timestamps = [p.get("timestamp") for p in data_points if p.get("timestamp") is not None]
        deltas = [b - a for a, b in zip(timestamps, timestamps[1:])]
        timestamps_regular = bool(deltas) and len({round(d, 6) for d in deltas}) == 1

        tag_values: Dict[str, set] = {}
        for p in data_points:
            for k, v in p.get("tags", {}).items():
                tag_values.setdefault(k, set()).add(str(v))

        field_types: Dict[str, str] = {}
        for p in data_points:
            for k, v in p.get("fields", {}).items():
                field_types[k] = type(v).__name__

        return {
            "num_points": len(data_points),
            "timestamps_regular": timestamps_regular,
            "tag_cardinality": {k: len(v) for k, v in tag_values.items()},
            "field_types": field_types,
            "recommended": {
                "timestamps": "delta" if timestamps_regular else "delta+zigzag",
                "tags": "rle/dictionary (low cardinality)",
                "float_fields": "gorilla",
            },
        }

    def benchmark_algorithms(
        self, data_points: List[Dict[str, Any]]
    ) -> Dict[str, CompressionStats]:
        """
        Benchmark all compression algorithms on sample data.

        Returns compression statistics for each algorithm.
        """
        results: Dict[str, CompressionStats] = {}

        def timed(fn):
            start = time.perf_counter()
            out = fn()
            return out, time.perf_counter() - start

        # Delta on the timestamp column.
        timestamps = [float(p["timestamp"]) for p in data_points if p.get("timestamp") is not None]
        if timestamps:
            enc, dt = timed(lambda: self.delta.encode_timestamps(timestamps))
            results["delta"] = CompressionStats(len(timestamps) * 8, len(enc), dt, 0.0, "delta")

        # RLE + dictionary on the first tag column.
        tag_cols: Dict[str, List[str]] = {}
        for p in data_points:
            for k, v in p.get("tags", {}).items():
                tag_cols.setdefault(k, []).append(str(v))
        if tag_cols:
            col = next(iter(tag_cols.values()))
            orig = len(json.dumps(col).encode("utf-8"))
            enc, dt = timed(lambda: self.rle.encode_values(col))
            results["rle"] = CompressionStats(orig, len(enc), dt, 0.0, "rle")
            enc2, dt2 = timed(lambda: self.dictionary.encode_strings(col)[0])
            results["dictionary"] = CompressionStats(orig, len(enc2), dt2, 0.0, "dictionary")

        # Gorilla on the first float field column.
        float_cols: Dict[str, List[float]] = {}
        for p in data_points:
            for k, v in p.get("fields", {}).items():
                if isinstance(v, float) and not isinstance(v, bool):
                    float_cols.setdefault(k, []).append(v)
        if float_cols:
            col_f = next(iter(float_cols.values()))
            enc, dt = timed(lambda: self.gorilla.encode_floats(col_f))
            results["gorilla"] = CompressionStats(len(col_f) * 8, len(enc), dt, 0.0, "gorilla")

        # General-purpose zlib on the whole payload (the container codec).
        raw = json.dumps(data_points, sort_keys=True).encode("utf-8")
        enc, dt = timed(lambda: zlib.compress(raw, level=9))
        results["zlib"] = CompressionStats(len(raw), len(enc), dt, 0.0, "zlib")

        return results

