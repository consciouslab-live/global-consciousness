#!/usr/bin/env python3
"""
Quantum Uploader Test Script
Test the new file-based quantum data uploader
"""

import time
import os
import json
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from src.services.quantum_uploader import QuantumUploader
from src.config.config_loader import get_config


def create_test_data_file(data_dir: str, num_bits: int = 10, suffix: str = "") -> str:
    """Create test data file"""
    data_points = []

    # Create a base timestamp for this batch (simulating when a batch was fetched from quantum API)
    base_timestamp = datetime.now(timezone.utc)

    for i in range(num_bits):
        # For testing purposes, add small increments to simulate quantum bit generation times
        # In real implementation, all bits in a batch would have the same fetch timestamp
        ts = base_timestamp + timedelta(microseconds=i * 100)
        # Generate proper ISO timestamp with Z suffix (replace +00:00 with Z)
        timestamp = ts.isoformat().replace("+00:00", "Z")
        bit = i % 2  # Alternating 0 and 1
        data_points.append({"timestamp": timestamp, "bit": bit})

    # Create file with unique name including microseconds and suffix
    now = datetime.now(timezone.utc)
    filename = f"bits_{now.strftime('%Y%m%d_%H%M%S')}_{now.microsecond}{suffix}.json"
    filepath = os.path.join(data_dir, filename)

    with open(filepath, "w") as f:
        json.dump(data_points, f, indent=4)

    print(f"✅ Created test data file: {filename} with {num_bits} bits")
    return filepath


def test_file_processing():
    """Test file processing functionality"""
    print("🧪 Testing file processing functionality...")

    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Create test data files with unique names
        create_test_data_file(temp_dir, 32, "_file1")
        time.sleep(0.1)  # Ensure different timestamps
        create_test_data_file(temp_dir, 32, "_file2")

        # Create uploader using configuration
        uploader = QuantumUploader(
            data_dir=temp_dir,
            upload_interval=get_config("quantum_uploader.upload_interval", 30),
        )

        # Test reading files - use correct method name
        uint32_data_points = uploader._read_and_accumulate_bits()
        # Calculate total bits from uint32 values (each represents 32 bits if we had 32+ bits)
        total_bits_processed = len(uint32_data_points) * 32 if uint32_data_points else 0
        print(
            f"✅ Processed {len(uint32_data_points)} uint32 values (representing {total_bits_processed} bits)"
        )

        # Check if files were deleted
        remaining_files = [f for f in os.listdir(temp_dir) if f.startswith("bits_")]
        print(f"✅ Remaining files: {len(remaining_files)} (should be 0)")

        # We have 64 bits total (32+32), should generate 2 uint32 values, and files should be deleted
        expected_uint32_count = 2
        return (
            len(uint32_data_points) == expected_uint32_count
            and len(remaining_files) == 0
        )

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)


def test_uploader_status():
    """Test uploader status functionality"""
    print("\n🧪 Testing uploader status functionality...")

    try:
        uploader = QuantumUploader()
        status = uploader.get_status()

        print(f"✅ Status retrieved successfully: {status}")

        # Check required fields
        required_fields = ["running", "pending_files", "stats"]
        missing_fields = [field for field in required_fields if field not in status]

        if missing_fields:
            print(f"❌ Missing fields: {missing_fields}")
            return False

        print("✅ All required fields are present")
        return True

    except Exception as e:
        print(f"❌ Status test failed: {e}")
        return False


def test_integration_with_proxy():
    """Test integration with quantum proxy"""
    print("\n🧪 Testing integration with quantum proxy...")

    # Check quantum_data directory - use the configured data directory
    data_dir = get_config("quantum_uploader.data_dir", "data/quantum_data")
    if not os.path.exists(data_dir):
        print(f"⚠️ Data directory {data_dir} does not exist")
        print("💡 Please ensure quantum_proxy.py is running and generating data files")
        return False

    # Check existing files
    files = [f for f in os.listdir(data_dir) if f.startswith("bits_")]
    print(f"📂 Found {len(files)} data files")

    if len(files) == 0:
        print("⚠️ No data files found")
        print("💡 Please ensure quantum_proxy.py is running and processing requests")
        return False

    # Try to create uploader
    try:
        uploader = QuantumUploader()
        status = uploader.get_status()
        print(f"✅ Uploader status: {status['pending_files']} pending files")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def test_environment_setup():
    """Test environment setup"""
    print("\n🧪 Testing environment setup...")

    # Check environment variables
    if not os.getenv("HF_TOKEN"):
        print("❌ Error: Please set HF_TOKEN environment variable")
        return False

    print("✅ HF_TOKEN is set")

    try:
        # Test import - use correct import path
        from src.services.quantum_uploader import QuantumUploader

        print("✅ QuantumUploader imported successfully")

        # Test Hugging Face login
        _ = QuantumUploader()
        print("✅ Hugging Face login successful")

        return True

    except Exception as e:
        print(f"❌ Environment setup test failed: {e}")
        return False


def main():
    """Main test function"""
    print("🌌 Quantum Data Uploader Test (File-based Architecture)")
    print("=" * 60)

    # Test 1: Environment setup
    success1 = test_environment_setup()

    # Test 2: File processing
    success2 = test_file_processing()

    # Test 3: Status functionality
    success3 = test_uploader_status()

    # Test 4: Integration with proxy
    success4 = test_integration_with_proxy()

    print("\n" + "=" * 60)
    print("📋 Test Results:")
    print(f"   Environment Setup Test: {'✅ Passed' if success1 else '❌ Failed'}")
    print(f"   File Processing Test: {'✅ Passed' if success2 else '❌ Failed'}")
    print(f"   Status Functionality Test: {'✅ Passed' if success3 else '❌ Failed'}")
    print(f"   Proxy Integration Test: {'✅ Passed' if success4 else '❌ Failed'}")

    if all([success1, success2, success3]):
        print("\n🎉 Core functionality tests passed!")
        if success4:
            print("🎉 Integration with quantum proxy is also working normally!")
        else:
            print(
                "💡 Tip: To fully test integration, please run quantum_proxy.py first"
            )
        return 0
    else:
        print("\n⚠️ Some tests failed, please check configuration.")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
