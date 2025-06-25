#!/usr/bin/env python3
"""
Quantum Uploader uint32 Test Script
Test the new optimized uint32 packing functionality
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
from src.services.quantum_uploader import QuantumUploader


def create_test_bits_for_uint32(data_dir: str, num_batches: int = 3) -> list:
    """Create test data files with exactly 32 bits each for uint32 testing"""
    created_files = []

    for batch_idx in range(num_batches):
        data_points = []

        # Create a base timestamp for this batch (without timezone info for proper formatting)
        base_timestamp = datetime.utcnow() + timedelta(seconds=batch_idx)

        # Create exactly 32 bits for one uint32 value
        for bit_idx in range(32):
            # Create alternating pattern: 10101010... for predictable uint32 values
            bit_value = bit_idx % 2
            # Create proper ISO timestamp
            bit_timestamp = base_timestamp + timedelta(microseconds=bit_idx * 100)
            timestamp = bit_timestamp.isoformat() + "Z"
            data_points.append({"timestamp": timestamp, "bit": bit_value})

        # Create filename
        filename = (
            f"bits_{base_timestamp.strftime('%Y%m%d_%H%M%S')}_{batch_idx:03d}.json"
        )
        filepath = os.path.join(data_dir, filename)

        with open(filepath, "w") as f:
            json.dump(data_points, f, indent=2)

        created_files.append(filepath)
        print(f"✅ Created test file: {filename} (32 bits)")

        # Calculate expected uint32 value for verification
        bits = [point["bit"] for point in data_points]
        expected_uint32 = 0
        for i, bit in enumerate(bits):
            if bit:
                expected_uint32 |= 1 << (31 - i)
        print(f"   Expected uint32 value: {expected_uint32} (0x{expected_uint32:08X})")

    return created_files


def test_uint32_conversion():
    """Test the uint32 conversion function"""
    print("\n🧪 Testing uint32 conversion...")

    # Create test uploader instance
    uploader = QuantumUploader()

    # Test case 1: All zeros
    all_zeros = [0] * 32
    result = uploader._bits_to_uint32(all_zeros)
    expected = 0
    assert result == expected, f"All zeros test failed: {result} != {expected}"
    print(f"✅ All zeros: {result} (0x{result:08X})")

    # Test case 2: All ones
    all_ones = [1] * 32
    result = uploader._bits_to_uint32(all_ones)
    expected = 0xFFFFFFFF
    assert result == expected, f"All ones test failed: {result} != {expected}"
    print(f"✅ All ones: {result} (0x{result:08X})")

    # Test case 3: Alternating pattern (01010101...)
    alternating = [i % 2 for i in range(32)]
    result = uploader._bits_to_uint32(alternating)
    expected = 0x55555555  # 01010101... in hex
    assert result == expected, f"Alternating test failed: {result} != {expected}"
    print(f"✅ Alternating: {result} (0x{result:08X})")

    # Test case 4: Single bit set (MSB)
    single_msb = [1] + [0] * 31
    result = uploader._bits_to_uint32(single_msb)
    expected = 0x80000000
    assert result == expected, f"Single MSB test failed: {result} != {expected}"
    print(f"✅ Single MSB: {result} (0x{result:08X})")

    print("✅ All uint32 conversion tests passed!")


def test_optimized_uploader():
    """Test the optimized uploader with uint32 packing"""
    print("\n🧪 Testing optimized uploader...")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary directory: {temp_dir}")

        # Create test uploader with shorter intervals for testing
        uploader = QuantumUploader(
            data_dir=temp_dir,
            upload_interval=2,  # 2 seconds for testing
            bits_per_upload=32,
        )

        # Create test data files
        created_files = create_test_bits_for_uint32(temp_dir, num_batches=2)
        print(f"📝 Created {len(created_files)} test files")

        # Test bit accumulation (without actually uploading to HF)
        print("🔄 Testing bit accumulation and uint32 packing...")

        # Read and accumulate bits
        uint32_data_points = uploader._read_and_accumulate_bits()

        print(f"📦 Packed {len(uint32_data_points)} uint32 values")

        # Verify results
        assert (
            len(uint32_data_points) == 2
        ), f"Expected 2 uint32 values, got {len(uint32_data_points)}"

        for i, data_point in enumerate(uint32_data_points):
            print(
                f"   uint32[{i}]: value={data_point['uint32_value']} (0x{data_point['uint32_value']:08X}), timestamp={data_point['timestamp']}"
            )

            # Verify timestamp is Unix timestamp
            assert isinstance(
                data_point["timestamp"], int
            ), "Timestamp should be Unix timestamp (int)"
            assert (
                data_point["timestamp"] > 1600000000
            ), "Timestamp should be reasonable Unix timestamp"

            # Verify uint32 value
            assert isinstance(
                data_point["uint32_value"], int
            ), "uint32_value should be integer"
            assert (
                0 <= data_point["uint32_value"] <= 0xFFFFFFFF
            ), "uint32_value should be in valid range"

        # Test accumulator status
        status = uploader.get_accumulator_status()
        print(f"📊 Accumulator status: {status}")

        # Verify files were deleted after processing
        remaining_files = [f for f in created_files if os.path.exists(f)]
        assert (
            len(remaining_files) == 0
        ), f"Expected all files to be deleted, but {len(remaining_files)} remain"

        print("✅ Optimized uploader test passed!")


def main():
    """Run all tests"""
    print("🧪 Quantum Uploader uint32 Tests")
    print("=" * 50)

    try:
        # Test uint32 conversion
        test_uint32_conversion()

        # Test optimized uploader
        test_optimized_uploader()

        print("\n" + "=" * 50)
        print("✅ All tests passed successfully!")
        print("🚀 uint32 optimization is working correctly")
        print("💡 Ready for high-frequency quantum data streaming")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
