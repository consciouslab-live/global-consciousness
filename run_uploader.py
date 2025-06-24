#!/usr/bin/env python3
"""
Quantum Uploader Runner
Simple startup script for running the quantum data uploader
"""

import sys
import signal
from quantum_uploader import QuantumUploader, logger
from config_loader import get_quantum_uploader_config, get_config


def signal_handler(sig, frame):
    """Handle interrupt signals"""
    print("\n🛑 Received interrupt signal, stopping...")
    sys.exit(0)


def main():
    """Main function"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    config = get_quantum_uploader_config()

    print("🌌 Quantum Bit Data Uploader")
    print("=" * 50)
    print("📋 Configuration:")
    print("   • Data collection frequency: Once per second")
    print(f"   • Upload frequency: Every {config['upload_interval'] // 3600} hour(s)")
    print(f"   • Target repository: {config['hf_repo']}")
    print("   • Data format: timestamp (UTC) + bit (0/1)")
    print("=" * 50)

    try:
        # Create and start uploader (using configuration defaults)
        uploader = QuantumUploader(
            batch_size=config[
                "small_batch_size"
            ],  # Use smaller batch size for run_uploader
        )

        uploader.start()

        print("🟢 Quantum data uploader started!")
        print("💡 Tip: Press Ctrl+C to stop the program")
        print("\n📊 Status information will be displayed every minute...")

        # Display status periodically
        import time

        status_interval = get_config("quantum_uploader.status_display_interval")

        while True:
            time.sleep(status_interval)
            uploader.print_status()

    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt...")
    except Exception as e:
        logger.error(f"❌ Program error: {e}")
        return 1
    finally:
        if "uploader" in locals():
            uploader.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
