#!/usr/bin/env python3
"""
Quantum Uploader Runner
Simple startup script for running the quantum data uploader
"""

import sys
import signal
from quantum_uploader import QuantumUploader, logger


def signal_handler(sig, frame):
    """Handle interrupt signals"""
    print("\n🛑 Received interrupt signal, stopping...")
    sys.exit(0)


def main():
    """Main function"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🌌 Quantum Bit Data Uploader")
    print("=" * 50)
    print("📋 Configuration:")
    print("   • Data collection frequency: Once per second")
    print("   • Upload frequency: Every 10 minutes")
    print("   • Target repository: consciouslab-live/quantum-bits")
    print("   • Data format: timestamp (UTC) + bit (0/1)")
    print("=" * 50)

    try:
        # Create and start uploader
        uploader = QuantumUploader(
            hf_repo="consciouslab-live/quantum-bits",
            upload_interval=600,  # Upload every 10 minutes
            batch_size=1000,  # Batch size limit
        )

        uploader.start()

        print("🟢 Quantum data uploader started!")
        print("💡 Tip: Press Ctrl+C to stop the program")
        print("\n📊 Status information will be displayed every minute...")

        # Display status every 60 seconds
        import time

        while True:
            time.sleep(60)
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
