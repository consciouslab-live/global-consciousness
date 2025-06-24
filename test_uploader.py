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
from datetime import datetime, timezone
from quantum_uploader import QuantumUploader


def create_test_data_file(data_dir: str, num_bits: int = 10) -> str:
    """Create test data file"""
    data_points = []

    for i in range(num_bits):
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        bit = i % 2  # Alternating 0 and 1
        data_points.append({"timestamp": timestamp, "bit": bit})
        time.sleep(0.1)  # Small interval to create different timestamps

    # Create file
    filename = f"bits_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
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
        # Create test data files
        create_test_data_file(temp_dir, 5)
        create_test_data_file(temp_dir, 3)

        # Create uploader
        uploader = QuantumUploader(
            hf_repo="consciouslab-live/quantum-bits",
            data_dir=temp_dir,
            upload_interval=30,
            batch_size=100,
        )

        # Test reading files
        data_points = uploader._read_data_files()
        print(f"✅ Read {len(data_points)} data points")

        # Check if files were deleted
        remaining_files = [f for f in os.listdir(temp_dir) if f.startswith("bits_")]
        print(f"✅ Remaining files: {len(remaining_files)} (should be 0)")

        return len(data_points) == 8 and len(remaining_files) == 0

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

    # Check quantum_data directory
    data_dir = "quantum_data"
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
        # Test import
        from quantum_uploader import QuantumUploader

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
