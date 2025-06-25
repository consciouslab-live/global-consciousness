#!/usr/bin/env python3
"""
Demo: Optimized Quantum Data Uploader with uint32 Packing
Demonstrates the new high-frequency quantum data streaming capability
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.services.quantum_uploader import QuantumUploader


def create_demo_quantum_data(data_dir: str, num_files: int = 5):
    """Create demo quantum data files to simulate quantum_proxy.py output"""
    print(f"🔧 Creating {num_files} demo quantum data files...")

    os.makedirs(data_dir, exist_ok=True)

    for file_idx in range(num_files):
        data_points = []
        base_time = datetime.utcnow() + timedelta(seconds=file_idx * 0.1)

        # Generate random-looking pattern for demo (not actual quantum data)
        for bit_idx in range(64):  # Create 64 bits per file
            # Simple LFSR-like pattern for demo purposes
            bit_value = ((file_idx * 17 + bit_idx * 23) % 3) % 2
            timestamp = (
                base_time + timedelta(microseconds=bit_idx * 1000)
            ).isoformat() + "Z"
            data_points.append({"timestamp": timestamp, "bit": bit_value})

        # Create filename matching quantum_proxy.py format
        filename = f"bits_{base_time.strftime('%Y%m%d_%H%M%S')}_{file_idx:03d}.json"
        filepath = os.path.join(data_dir, filename)

        with open(filepath, "w") as f:
            json.dump(data_points, f, indent=2)

        print(f"   📄 Created {filename} ({len(data_points)} quantum bits)")

    print(f"✅ Demo data ready in {data_dir}")


def demo_uint32_optimization():
    """Demonstrate the uint32 optimization"""
    print("\n🌌 QUANTUM DATA UINT32 OPTIMIZATION DEMO")
    print("=" * 60)

    # Create temporary demo directory
    demo_dir = "data/demo_quantum"

    try:
        # Create demo data
        create_demo_quantum_data(demo_dir)

        # Create optimized uploader instance
        print("\n🚀 Initializing Optimized Quantum Uploader...")
        uploader = QuantumUploader(
            data_dir=demo_dir,
            upload_interval=1,  # 1 second intervals
            bits_per_upload=32,  # 32 bits = 1 uint32
        )

        print("\n📊 OPTIMIZATION BENEFITS:")
        print("   • Storage: 32 bits → 1 uint32 value (87.5% size reduction)")
        print("   • Timestamps: ISO strings → Unix int64 (faster processing)")
        print("   • Upload frequency: Every 1 second (real-time streaming)")
        print("   • Data integrity: Exact quantum bit fetch timestamps preserved")

        # Process available data
        print("\n🔄 Processing demo quantum data...")
        uint32_data_points = uploader._read_and_accumulate_bits()

        if uint32_data_points:
            print(f"📦 Successfully packed {len(uint32_data_points)} uint32 values!")

            print("\n🔍 SAMPLE PACKED DATA:")
            for i, data_point in enumerate(uint32_data_points[:3]):  # Show first 3
                timestamp = data_point["timestamp"]
                uint32_val = data_point["uint32_value"]
                dt = datetime.fromtimestamp(timestamp, timezone.utc)

                print(f"   [{i + 1}] Unix Timestamp: {timestamp}")
                print(f"       Human Time: {dt.strftime('%Y-%m-%d %H:%M:%S.%f')} UTC")
                print(f"       uint32 Value: {uint32_val} (0x{uint32_val:08X})")
                print(f"       Binary: {format(uint32_val, '032b')}")
                print()

            if len(uint32_data_points) > 3:
                print(f"   ... and {len(uint32_data_points) - 3} more uint32 values")

            # Show accumulator status
            status = uploader.get_accumulator_status()
            print("📈 ACCUMULATOR STATUS:")
            print(f"   • Remaining bits: {status['remaining_bits']}")
            print(
                f"   • Complete batches ready: {status['complete_uint32_batches_ready']}"
            )
            print(
                f"   • Next uint32 progress: {status['next_uint32_completion_progress']}"
            )

        else:
            print("📭 No complete uint32 batches available (need at least 32 bits)")

        # Show efficiency comparison
        print("\n💡 EFFICIENCY COMPARISON:")
        total_bits = len(uint32_data_points) * 32

        # Old format: JSON with string timestamps and int8 bits
        old_size_estimate = total_bits * (
            25 + 1
        )  # ~25 chars for ISO timestamp + 1 byte for bit

        # New format: Unix timestamp (8 bytes) + uint32 (4 bytes) per 32 bits
        new_size_estimate = len(uint32_data_points) * (8 + 4)

        if old_size_estimate > 0:
            efficiency = (1 - new_size_estimate / old_size_estimate) * 100
            print(f"   Old format estimate: ~{old_size_estimate:,} bytes")
            print(f"   New format estimate: ~{new_size_estimate:,} bytes")
            print(f"   Storage efficiency: ~{efficiency:.1f}% reduction")

        print("\n✅ Demo completed successfully!")
        print("🚀 Ready for production quantum data streaming!")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise

    finally:
        # Cleanup demo files
        try:
            import shutil

            if os.path.exists(demo_dir):
                shutil.rmtree(demo_dir)
                print(f"🧹 Cleaned up demo directory: {demo_dir}")
        except:  # noqa: E722
            pass


def main():
    """Run the demonstration"""
    try:
        demo_uint32_optimization()
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
