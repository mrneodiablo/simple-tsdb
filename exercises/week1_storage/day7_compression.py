#!/usr/bin/env python3
"""
Day 7: Basic Compression
=======================

Problem: Implement simple compression algorithms for time-series data

Learning Objectives:
- Understand compression trade-offs for time-series data
- Implement delta encoding for timestamps
- Create run-length encoding for repetitive data
- Design compression/decompression interfaces
- Measure compression ratios and performance

Real-World Connection:
InfluxDB achieves 90%+ compression using specialized algorithms like Gorilla compression
for floats and delta encoding for timestamps. Understanding compression helps you
optimize storage costs and I/O performance.
"""

import struct
import time
import json
import gzip
import zlib
from typing import List, Dict, Any, Tuple, Union, Optional
from dataclasses import dataclass
from enum import Enum
import math


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
        # TODO: Encode each run as (value, count)
        
        if not isinstance(values, int):
            raise TypeError("values must contain only a single type of value")

        if not values:
            return b""
        
        encoded = bytearray()
        current_value = values[0]
        count = 1
        endcode_variable = DeltaEncoder().encode_variable_int  # Reuse variable int encoding
        for value in values[1:]:
            # TODO: Find runs of identical values
            if value == current_value:
                count += 1
            else:
                # TODO: Use efficient encoding for counts
                encoded.extend(endcode_variable(count))
                encoded.extend(current_value.encode('utf-8'))
                current_value = value
                count = 1
        encoded.extend(endcode_variable(count))
        encoded.extend(current_value.encode('utf-8'))
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
        # TODO: Initialize all compression algorithms
        pass

    def compress_data_points(
        self, data_points: List[Dict[str, Any]]
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress list of time-series data points.

        Args:
            data_points: List of data points

        Returns:
            Tuple of (compressed_data, compression_metadata)

        Strategy:
        1. Separate timestamps, tags, and fields
        2. Choose optimal compression for each data type
        3. Combine compressed streams with metadata
        """
        # TODO: Separate data into columns (timestamps, tags, fields)
        # TODO: Choose compression algorithm for each column
        # TODO: Compress each column separately
        # TODO: Combine into final compressed format
        pass

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
        # TODO: Parse compression metadata
        # TODO: Decompress each column using appropriate algorithm
        # TODO: Reconstruct original data points
        pass

    def analyze_compression_potential(
        self, data_points: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze data to predict compression ratios for different algorithms.

        Returns analysis of which algorithms would work best.
        """
        # TODO: Analyze timestamp patterns
        # TODO: Analyze tag value repetition
        # TODO: Analyze field value characteristics
        # TODO: Predict compression ratios for each algorithm
        pass

    def benchmark_algorithms(
        self, data_points: List[Dict[str, Any]]
    ) -> Dict[str, CompressionStats]:
        """
        Benchmark all compression algorithms on sample data.

        Returns compression statistics for each algorithm.
        """
        # TODO: Test each compression algorithm
        # TODO: Measure compression ratio and speed
        # TODO: Return statistics for comparison
        pass


def test_compression():
    """
    Test cases for compression algorithms.
    """
    print("Testing Time-Series Compression...")

    # Test 1: Delta encoding for timestamps
    delta_encoder = DeltaEncoder()

    # Generate realistic timestamp sequence
    base_timestamp = time.time()
    timestamps = [base_timestamp + i * 60 for i in range(1000)]  # 1-minute intervals

    compressed_ts = delta_encoder.encode_timestamps(timestamps)
    decompressed_ts = delta_encoder.decode_timestamps(compressed_ts)

    assert len(decompressed_ts) == len(
        timestamps
    ), "Should decode same number of timestamps"
    for orig, decoded in zip(timestamps, decompressed_ts):
        assert abs(orig - decoded) < 0.001, f"Timestamp mismatch: {orig} vs {decoded}"

    original_size = len(timestamps) * 8  # 8 bytes per double
    compressed_size = len(compressed_ts)
    compression_ratio = original_size / compressed_size

    print(f"✓ Test 1 passed: Delta encoding - {compression_ratio:.1f}x compression")

    # Test 2: Run-length encoding
    rle_encoder = RunLengthEncoder()

    # Generate data with runs
    repetitive_data = []
    for i in range(10):
        value = f"server{i % 3}"  # Only 3 unique values
        repetitive_data.extend([value] * 20)  # 20 repetitions each

    compressed_rle = rle_encoder.encode_values(repetitive_data)
    decompressed_rle = rle_encoder.decode_values(compressed_rle)

    assert decompressed_rle == repetitive_data, "RLE should preserve data exactly"

    # Analyze compression effectiveness
    analysis = rle_encoder.analyze_runs(repetitive_data)
    print(
        f"✓ Test 2 passed: Run-length encoding - {analysis.get('estimated_ratio', 1.0):.1f}x estimated"
    )

    # Test 3: Gorilla compression for floats
    gorilla = GorillaCompressor()

    # Generate realistic sensor data (gradual changes)
    float_values = []
    base_value = 23.5  # Temperature in Celsius
    for i in range(100):
        # Add small random variation
        import random

        variation = random.gauss(0, 0.5)  # Small variation
        float_values.append(base_value + variation)
        base_value += random.gauss(0, 0.1)  # Slow drift

    try:
        compressed_floats = gorilla.encode_floats(float_values)
        decompressed_floats = gorilla.decode_floats(compressed_floats)

        # Check approximate equality (floating point precision)
        for orig, decoded in zip(float_values, decompressed_floats):
            assert abs(orig - decoded) < 0.001, f"Float mismatch: {orig} vs {decoded}"

        original_float_size = len(float_values) * 8
        compressed_float_size = len(compressed_floats)
        float_ratio = original_float_size / compressed_float_size

        print(f"✓ Test 3 passed: Gorilla compression - {float_ratio:.1f}x compression")
    except NotImplementedError:
        print("⚠️  Test 3 skipped: Gorilla compression not implemented yet")

    # Test 4: Dictionary compression
    dict_compressor = DictionaryCompressor()

    # Generate strings with limited vocabulary
    vocabularies = ["server1", "server2", "server3", "db01", "db02", "web01"]
    string_data = []
    for _ in range(200):
        import random

        string_data.append(random.choice(vocabularies))

    compressed_strings, dictionary = dict_compressor.encode_strings(string_data)
    decompressed_strings = dict_compressor.decode_strings(
        compressed_strings, dictionary
    )

    assert (
        decompressed_strings == string_data
    ), "Dictionary compression should preserve data"
    print(f"✓ Test 4 passed: Dictionary compression - {len(dictionary)} unique values")

    # Test 5: Full time-series compression
    compressor = TimeSeriesCompressor()

    # Generate realistic time-series data points
    test_points = []
    base_ts = time.time()

    for i in range(100):
        point = {
            "timestamp": base_ts + i * 60,
            "tags": {
                "host": f"server{i % 3}",
                "region": "us-west" if i % 2 == 0 else "us-east",
                "environment": "production",
            },
            "fields": {
                "cpu_usage": 50.0 + (i % 20) + random.gauss(0, 2),
                "memory_mb": 1000 + i * 10,
                "disk_io": random.randint(100, 1000),
                "online": True,
            },
        }
        test_points.append(point)

    # Test compression
    compressed_data, metadata = compressor.compress_data_points(test_points)
    decompressed_points = compressor.decompress_data_points(compressed_data, metadata)

    assert len(decompressed_points) == len(
        test_points
    ), "Should decompress same number of points"

    # Calculate overall compression ratio
    original_json = json.dumps(test_points).encode("utf-8")
    overall_ratio = len(original_json) / len(compressed_data)

    print(f"✓ Test 5 passed: Full compression - {overall_ratio:.1f}x compression")

    # Test 6: Compression analysis
    analysis = compressor.analyze_compression_potential(test_points)
    assert isinstance(analysis, dict), "Should return analysis dictionary"
    print(f"✓ Test 6 passed: Compression analysis - {len(analysis)} metrics analyzed")

    # Test 7: Algorithm benchmarking
    benchmarks = compressor.benchmark_algorithms(
        test_points[:20]
    )  # Small sample for speed
    assert isinstance(benchmarks, dict), "Should return benchmark results"

    print("✓ Test 7 passed: Algorithm benchmarking")
    for algo, stats in benchmarks.items():
        print(
            f"   {algo}: {stats.compression_ratio:.1f}x ratio, {stats.space_savings:.1f}% savings"
        )

    print("\n🎉 All compression tests passed!")
    print("Your compression system correctly handles:")
    print("  - Delta encoding for timestamps and integers")
    print("  - Run-length encoding for repetitive data")
    print("  - Gorilla compression for floating-point values")
    print("  - Dictionary compression for limited vocabulary strings")
    print("  - Automatic algorithm selection and benchmarking")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement all TODO methods in the compression classes
    2. Run this file to test: python day7_compression.py
    3. All tests should pass (some may be skipped if algorithms not implemented)
    4. Experiment with different data patterns

    Success criteria:
    - Delta encoding achieves good compression on timestamps
    - RLE works well for repetitive data
    - Dictionary compression handles string vocabularies
    - Full compression system combines algorithms effectively
    - Benchmarking provides useful performance data

    Next steps:
    - Move to Week 1 Integration Lab: labs/week1_lab.py
    - Think about: How would you adapt compression for different data patterns?
    - Consider: What are the trade-offs between compression ratio and CPU usage?
    """
    test_compression()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts Learned:

1. Compression Algorithm Selection:
   - Different algorithms for different data types
   - Time-series data has specific patterns (timestamps, gradual changes)
   - Algorithm effectiveness depends on data characteristics
   - Trade-offs between compression ratio and CPU usage

2. Specialized Time-Series Compression:
   - Delta encoding for monotonic sequences (timestamps)
   - Gorilla compression for floating-point sensor data
   - Run-length encoding for repetitive categorical data
   - Dictionary compression for limited vocabulary strings

3. Columnar Compression:
   - Separate compression for different fields
   - Better compression ratios than row-based compression
   - Enables different algorithms per column
   - Simplifies decompression for partial reads

4. Performance Considerations:
   - Compression CPU cost vs I/O savings
   - Memory usage during compression/decompression
   - Block size optimization
   - Streaming vs batch compression

Connection to InfluxDB:
- InfluxDB TSM files use specialized compression per field type
- Gorilla compression achieves 90%+ reduction for floats
- Delta encoding used extensively for timestamps
- Block-level compression enables partial reads

Real-World Impact:
- Storage cost reduction (especially in cloud)
- Network bandwidth savings
- Cache efficiency (more data fits in memory)
- I/O performance improvement

Advanced Topics:
- Adaptive compression based on data patterns
- Multi-level compression (algorithm + general purpose)
- Streaming compression for real-time data
- Hardware acceleration (SIMD, GPU)
- Approximate compression for analytics workloads

Engineering Trade-offs:
- Compression ratio vs CPU usage
- Encode speed vs decode speed
- Memory usage vs compression effectiveness
- Implementation complexity vs maintenance
"""
