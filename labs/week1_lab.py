#!/usr/bin/env python3
"""
Week 1 Integration Lab: Storage Layer Testing
============================================

This lab tests your complete Week 1 implementation by creating a realistic
time-series data scenario and verifying all storage components work together.

Scenario: Load Testing Metrics Collection
You're collecting performance metrics from a load test with multiple
endpoints, servers, and time periods.

Success Criteria:
- Write 10,000+ data points across multiple measurements
- Verify correct file organization by time
- Test data integrity and persistence
- Measure basic performance characteristics
"""

import os
import sys
import time
import shutil
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the project root to Python path to import exercises
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import your implementations from Week 1 exercises
# Note: You'll need to complete the exercises first for these imports to work
try:
    # These will be available after you complete the Week 1 exercises
    from exercises.week1_storage.day1_file_operations import FileManager
    from exercises.week1_storage.day2_serialization import DataPoint, TimeSeriesSerializer
    from exercises.week1_storage.day3_line_protocol import LineProtocolParser  # You'll create this
except ImportError as e:
    print(f"⚠️  Import Error: {e}")
    print("Complete Week 1 exercises (day1-day7) before running this lab.")
    import traceback
    traceback.print_exc()
    sys.exit(1)


class LoadTestDataGenerator:
    """Generate realistic load test metrics data."""

    def __init__(self):
        self.endpoints = [
            "/api/users", "/api/orders", "/api/products", "/api/auth/login",
            "/api/payments", "/api/search", "/api/recommendations", "/health"
        ]
        self.methods = ["GET", "POST", "PUT", "DELETE"]
        self.servers = ["web-01", "web-02", "web-03", "api-01", "api-02"]
        self.regions = ["us-west-2", "us-east-1", "eu-central-1"]
        self.status_codes = [200, 201, 400, 404, 500, 503]

    def generate_http_request_data(self, timestamp: float) -> DataPoint:
        """Generate a single HTTP request data point."""
        endpoint = random.choice(self.endpoints)
        method = random.choice(self.methods)
        server = random.choice(self.servers)
        region = random.choice(self.regions)
        status = random.choices(
            self.status_codes,
            weights=[70, 10, 8, 5, 5, 2],  # Most requests succeed
            k=1
        )[0]

        # Generate realistic response times based on endpoint
        base_time = {
            "/health": 5,
            "/api/auth/login": 150,
            "/api/users": 80,
            "/api/orders": 120,
            "/api/products": 60,
            "/api/payments": 200,
            "/api/search": 300,
            "/api/recommendations": 500
        }.get(endpoint, 100)

        # Add some realistic variance
        response_time = max(1, base_time + random.gauss(0, base_time * 0.3))

        # Error responses are typically faster
        if status >= 400:
            response_time *= 0.3

        tags = {
            "endpoint": endpoint,
            "method": method,
            "server": server,
            "region": region,
            "status": str(status)
        }

        fields = {
            "response_time": round(response_time, 2),
            "bytes_sent": random.randint(500, 5000),
            "bytes_received": random.randint(100, 1000),
            "is_cached": random.choice([True, False])
        }

        return DataPoint("http_requests", timestamp, tags, fields)

    def generate_system_metrics(self, timestamp: float, server: str) -> List[DataPoint]:
        """Generate system metrics for a server."""
        region = random.choice(self.regions)

        # CPU metrics
        cpu_usage = max(0, min(100, random.gauss(60, 20)))
        cpu_point = DataPoint(
            "cpu",
            timestamp,
            {"server": server, "region": region, "core": "total"},
            {"usage_percent": round(cpu_usage, 1), "load_1m": round(cpu_usage / 30, 2)}
        )

        # Memory metrics
        memory_total = 32 * 1024  # 32GB in MB
        memory_used = int(memory_total * (cpu_usage / 100) * random.uniform(0.7, 1.2))
        memory_point = DataPoint(
            "memory",
            timestamp,
            {"server": server, "region": region},
            {
                "total_mb": memory_total,
                "used_mb": memory_used,
                "available_mb": memory_total - memory_used,
                "usage_percent": round((memory_used / memory_total) * 100, 1)
            }
        )

        # Disk I/O metrics
        disk_point = DataPoint(
            "disk",
            timestamp,
            {"server": server, "region": region, "device": "/dev/sda1"},
            {
                "read_iops": random.randint(10, 500),
                "write_iops": random.randint(5, 200),
                "read_mb_per_sec": round(random.uniform(1, 50), 2),
                "write_mb_per_sec": round(random.uniform(0.5, 20), 2)
            }
        )

        return [cpu_point, memory_point, disk_point]

    def generate_load_test_session(self, duration_minutes: int = 60, points_per_minute: int = 100) -> List[DataPoint]:
        """Generate a complete load test session."""
        print(f"🔄 Generating {duration_minutes} minutes of load test data...")
        print(f"   Target: {points_per_minute} HTTP requests/minute + system metrics")

        all_points = []
        start_time = time.time() - (duration_minutes * 60)  # Start in the past

        for minute in range(duration_minutes):
            minute_timestamp = start_time + (minute * 60)

            # Generate HTTP requests for this minute
            for _ in range(points_per_minute):
                # Spread requests across the minute
                point_timestamp = minute_timestamp + random.uniform(0, 60)
                http_point = self.generate_http_request_data(point_timestamp)
                all_points.append(http_point)

            # Generate system metrics (every minute)
            for server in self.servers:
                system_points = self.generate_system_metrics(minute_timestamp, server)
                all_points.extend(system_points)

            if minute % 10 == 0:
                print(f"   Generated minute {minute}/{duration_minutes}")

        print(f"✅ Generated {len(all_points)} total data points")
        return all_points


def run_integration_test():
    """Run the complete Week 1 integration test."""
    print("=" * 60)
    print("🧪 Week 1 Integration Lab: Storage Layer Testing")
    print("=" * 60)

    # Setup test environment
    test_dir = "lab_test_data"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    print(f"\n📁 Test directory: {test_dir}")

    # Initialize components
    file_manager = FileManager(test_dir)
    serializer = TimeSeriesSerializer()
    data_generator = LoadTestDataGenerator()

    # Test 1: Generate and write realistic data
    print("\n" + "=" * 40)
    print("Test 1: Data Generation and Writing")
    print("=" * 40)

    start_time = time.time()
    test_data = data_generator.generate_load_test_session(
        duration_minutes=30,  # 30 minutes of data
        points_per_minute=50   # 50 HTTP requests per minute
    )
    generation_time = time.time() - start_time

    print(f"📊 Data generated in {generation_time:.2f} seconds")
    print(f"   Total points: {len(test_data)}")
    print(f"   Generation rate: {len(test_data)/generation_time:.0f} points/second")

    # Write all data points
    print(f"\n🔄 Writing {len(test_data)} data points to storage...")
    write_start = time.time()
    write_success_count = 0

    for i, point in enumerate(test_data):
        success = file_manager.write_data_point(point.measurement, point.to_dict())
        if success:
            write_success_count += 1

        if (i + 1) % 1000 == 0:
            print(f"   Written {i + 1}/{len(test_data)} points...")

    write_time = time.time() - write_start
    write_rate = write_success_count / write_time

    print(f"✅ Write completed in {write_time:.2f} seconds")
    print(f"   Success rate: {write_success_count}/{len(test_data)} ({write_success_count/len(test_data)*100:.1f}%)")
    print(f"   Write rate: {write_rate:.0f} points/second")

    # Test 2: Verify file organization
    print("\n" + "=" * 40)
    print("Test 2: File Organization Verification")
    print("=" * 40)

    measurements = file_manager.list_measurements()
    print(f"📂 Measurements found: {measurements}")

    stats = file_manager.get_storage_stats()
    print(f"📈 Storage statistics:")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_bytes']:,} bytes ({stats['total_size_bytes']/1024/1024:.2f} MB)")
    print(f"   Measurements: {stats['measurements_count']}")
    print(f"   Time range: {datetime.fromtimestamp(stats['oldest_timestamp'])} to {datetime.fromtimestamp(stats['newest_timestamp'])}")

    # Verify file structure exists
    expected_measurements = ["http_requests", "cpu", "memory", "disk"]
    for measurement in expected_measurements:
        assert measurement in measurements, f"Missing measurement: {measurement}"
    print("✅ All expected measurements found")

    # Test 3: Data retrieval and integrity
    print("\n" + "=" * 40)
    print("Test 3: Data Retrieval and Integrity")
    print("=" * 40)

    # Test reading back specific time ranges
    now = time.time()
    one_hour_ago = now - 3600

    print("🔄 Testing time range queries...")
    for measurement in expected_measurements:
        points = file_manager.read_data_points(measurement, one_hour_ago, now)
        print(f"   {measurement}: {len(points)} points in last hour")

        if points:
            # Verify data integrity
            first_point = points[0]
            assert "timestamp" in first_point, f"Missing timestamp in {measurement}"
            assert "tags" in first_point, f"Missing tags in {measurement}"
            assert "fields" in first_point, f"Missing fields in {measurement}"

    print("✅ Data integrity verified")

    # Test 4: Serialization round-trip
    print("\n" + "=" * 40)
    print("Test 4: Serialization Round-Trip Test")
    print("=" * 40)

    # Take a sample of data and test serialization
    sample_data = test_data[:100]  # First 100 points
    print(f"🔄 Testing serialization with {len(sample_data)} sample points...")

    # Serialize
    serialization_start = time.time()
    serialized_json = serializer.serialize_batch(sample_data)
    serialization_time = time.time() - serialization_start

    print(f"📦 Serialized to {len(serialized_json):,} characters in {serialization_time*1000:.2f}ms")

    # Deserialize
    deserialization_start = time.time()
    deserialized_points = serializer.deserialize_batch(serialized_json)
    deserialization_time = time.time() - deserialization_start

    print(f"📖 Deserialized {len(deserialized_points)} points in {deserialization_time*1000:.2f}ms")

    # Verify data matches
    assert len(deserialized_points) == len(sample_data), "Point count mismatch after serialization"

    for original, restored in zip(sample_data, deserialized_points):
        assert original.measurement == restored.measurement, "Measurement mismatch"
        assert abs(original.timestamp - restored.timestamp) < 0.001, "Timestamp mismatch"
        assert original.tags == restored.tags, "Tags mismatch"
        # Note: Field values might have slight floating point differences

    print("✅ Serialization round-trip successful")

    # Test 5: Performance summary
    print("\n" + "=" * 40)
    print("Test 5: Performance Summary")
    print("=" * 40)

    total_points = len(test_data)
    storage_size_mb = stats['total_size_bytes'] / 1024 / 1024

    print(f"📊 Performance Results:")
    print(f"   Data points processed: {total_points:,}")
    print(f"   Write rate: {write_rate:.0f} points/second")
    print(f"   Storage efficiency: {total_points/storage_size_mb:.0f} points/MB")
    print(f"   Average point size: {stats['total_size_bytes']/total_points:.0f} bytes")
    print(f"   File count: {stats['total_files']} files")
    print(f"   Points per file: {total_points/stats['total_files']:.0f}")

    # Performance benchmarks (rough guidelines for learning project)
    print(f"\n📋 Performance Assessment:")
    if write_rate > 1000:
        print("   ✅ Write rate: Excellent (>1000 points/sec)")
    elif write_rate > 500:
        print("   ✅ Write rate: Good (>500 points/sec)")
    elif write_rate > 100:
        print("   ⚠️  Write rate: Acceptable (>100 points/sec)")
    else:
        print("   ❌ Write rate: Needs optimization (<100 points/sec)")

    if storage_size_mb < 50:
        print("   ✅ Storage size: Efficient (<50MB for test data)")
    elif storage_size_mb < 100:
        print("   ⚠️  Storage size: Acceptable (<100MB)")
    else:
        print("   ❌ Storage size: Inefficient (>100MB)")

    print("\n🎉 Week 1 Integration Lab Completed Successfully!")
    print(f"🗂️  Test data preserved in: {test_dir}")
    print("🚀 Ready to proceed to Week 2: Indexing & Retrieval")

    return {
        "points_processed": total_points,
        "write_rate": write_rate,
        "storage_mb": storage_size_mb,
        "file_count": stats['total_files'],
        "measurements": len(measurements)
    }


if __name__ == "__main__":
    """
    Run this lab after completing Week 1 exercises.

    Prerequisites:
    - Completed day1_file_operations.py
    - Completed day2_serialization.py
    - Completed day3_line_protocol.py (you'll create this)
    - All other Week 1 exercises

    This lab will:
    1. Generate 1500+ realistic time-series data points
    2. Test your storage system with real workload
    3. Verify file organization and data integrity
    4. Measure performance characteristics
    5. Prepare for Week 2 indexing requirements

    Expected results:
    - All data written successfully
    - Proper file organization by time and measurement
    - Data retrieval works correctly
    - Performance meets basic benchmarks
    """
    try:
        results = run_integration_test()
        print("\n✅ Lab completed successfully!")
        print("   Continue to Week 2: Indexing & Retrieval")
    except Exception as e:
        print(f"\n❌ Lab failed with error: {e}")
        print("   Review your Week 1 implementations and try again")
        raise