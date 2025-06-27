import os
import time
import threading
import logging
import json
import glob
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from datasets import Dataset, Features, Value
from huggingface_hub import login
from dateutil.parser import parse as parse_datetime
from src.config.config_loader import get_quantum_uploader_config, get_config

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QuantumUploader:
    """
    Quantum data uploader that reads data files from quantum_proxy.py and uploads to Hugging Face
    Optimized for efficient storage: 32 bits per second packed as uint32 with Unix timestamps
    """

    def __init__(
        self,
        hf_repo: Optional[str] = None,
        data_dir: Optional[str] = None,
        upload_interval: Optional[int] = None,  # seconds between uploads
        bits_per_upload: Optional[
            int
        ] = None,  # bits to collect per upload (32 for uint32)
    ):
        """
        Initialize quantum uploader

        Args:
            hf_repo: Hugging Face repository name (if None, uses config)
            data_dir: Directory containing data files from quantum_proxy.py (if None, uses config)
            upload_interval: Seconds between uploads (if None, defaults to 1 second)
            bits_per_upload: Bits to collect per upload (if None, defaults to 32 for uint32)
        """
        # Load configuration
        uploader_config = get_quantum_uploader_config()

        self.hf_repo = hf_repo or uploader_config["hf_repo"]
        self.data_dir = data_dir or uploader_config["data_dir"]
        # Override config for optimized uploading: 1 second intervals, 32 bits per upload
        self.upload_interval = upload_interval or 1  # 1 second for real-time streaming
        self.bits_per_upload = bits_per_upload or 32  # 32 bits = 1 uint32

        # Control flags
        self.running = False
        self.upload_thread = None

        # Statistics
        self.stats = {
            "total_uint32_uploaded": 0,  # Count of uint32 values uploaded
            "total_bits_uploaded": 0,  # Total individual bits uploaded
            "total_uploads": 0,
            "total_files_processed": 0,
            "last_upload_time": None,
            "upload_errors": 0,
            "file_errors": 0,
            "incomplete_batches": 0,  # Batches with < 32 bits
        }

        # Bit accumulator for building uint32 values
        self.bit_accumulator: List[Dict] = []
        self.accumulator_lock = threading.Lock()

        # Login to Hugging Face
        self._login_hf()

        logger.info("🚀 QuantumUploader initialized (Optimized Mode)")
        logger.info(f"   Repository: {self.hf_repo}")
        logger.info(f"   Data Directory: {self.data_dir}")
        logger.info(f"   Upload interval: {self.upload_interval}s")
        logger.info(f"   Bits per upload: {self.bits_per_upload} (uint32 packing)")
        logger.info("   📦 32 quantum bits → 1 uint32 value per second")

    def _login_hf(self):
        """Login to Hugging Face"""
        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError("HF_TOKEN environment variable is required")

        try:
            login(token=hf_token)
            logger.info("✅ Successfully logged in to Hugging Face")
        except Exception as e:
            logger.error(f"❌ Failed to login to Hugging Face: {e}")
            raise

    def _bits_to_uint32(self, bits: List[int]) -> int:
        """
        Convert list of 32 bits to uint32 integer

        Args:
            bits: List of 32 bits (0 or 1)

        Returns:
            uint32 integer value
        """
        if len(bits) != 32:
            raise ValueError(f"Expected 32 bits, got {len(bits)}")

        uint32_value = 0
        for i, bit in enumerate(bits):
            if bit:
                uint32_value |= 1 << (31 - i)  # MSB first

        return uint32_value

    def _read_and_accumulate_bits(self) -> List[Dict]:
        """
        Read available data files and accumulate bits for uint32 packing
        Returns list of uint32 data points ready for upload
        """
        uint32_data_points = []

        try:
            # Find all JSON files in data directory
            pattern = os.path.join(self.data_dir, "bits_*.json")
            files = glob.glob(pattern)

            if not files:
                logger.debug(f"📭 No data files found in {self.data_dir}")
                return []

            # Process files in chronological order
            files.sort()

            for filepath in files:
                try:
                    with open(filepath, "r") as f:
                        file_data = json.load(f)

                    if isinstance(file_data, list):
                        with self.accumulator_lock:
                            # Add bits to accumulator
                            self.bit_accumulator.extend(file_data)

                            # Process complete uint32 batches
                            while len(self.bit_accumulator) >= self.bits_per_upload:
                                # Take first 32 bits
                                batch_bits = self.bit_accumulator[
                                    : self.bits_per_upload
                                ]
                                self.bit_accumulator = self.bit_accumulator[
                                    self.bits_per_upload :
                                ]

                                # Convert to uint32
                                bits_only = [item["bit"] for item in batch_bits]
                                uint32_value = self._bits_to_uint32(bits_only)

                                # Use timestamp from first bit in the batch
                                first_bit_timestamp = batch_bits[0]["timestamp"]
                                # Convert ISO timestamp to Unix timestamp
                                if isinstance(first_bit_timestamp, str):
                                    dt = parse_datetime(first_bit_timestamp)
                                    unix_timestamp = int(dt.timestamp())
                                else:
                                    unix_timestamp = int(first_bit_timestamp)

                                uint32_data_points.append(
                                    {
                                        "timestamp": unix_timestamp,
                                        "uint32_value": uint32_value,
                                    }
                                )

                        # Delete processed file
                        os.remove(filepath)
                        logger.debug(
                            f"📄 Processed and removed {os.path.basename(filepath)}"
                        )

                    else:
                        logger.warning(f"⚠️ Invalid data format in {filepath}")

                except Exception as e:
                    logger.error(f"❌ Error processing file {filepath}: {e}")
                    self.stats["file_errors"] += 1

            if uint32_data_points:
                logger.info(
                    f"✅ Packed {len(uint32_data_points)} uint32 values from quantum bits"
                )

        except Exception as e:
            logger.error(f"❌ Error reading and accumulating bits: {e}")
            self.stats["file_errors"] += 1

        return uint32_data_points

    def _upload_uint32_data(self, uint32_data_points: List[Dict]):
        """Upload uint32 data points to Hugging Face"""
        if not uint32_data_points:
            logger.debug("📭 No uint32 data to upload")
            return

        try:
            logger.info(
                f"📤 Uploading {len(uint32_data_points)} uint32 values to Hugging Face..."
            )

            # Define dataset features for optimized storage
            features = Features(
                {
                    "timestamp": Value("int64"),  # Unix timestamp (seconds since 1970)
                    "uint32_value": Value(
                        "uint32"
                    ),  # 32 quantum bits packed as single uint32
                }
            )

            # Create dataset
            dataset = Dataset.from_list(uint32_data_points, features=features)

            # Determine split name (date and hour) for organization
            now = datetime.now(timezone.utc)
            split_name = f"uint32_{now.strftime('%Y%m%d_%H')}"

            # Upload to Hugging Face
            dataset.push_to_hub(self.hf_repo, split=split_name)

            # Update statistics
            self.stats["total_uploads"] += 1
            self.stats["total_uint32_uploaded"] += len(uint32_data_points)
            self.stats["total_bits_uploaded"] += len(uint32_data_points) * 32
            self.stats["last_upload_time"] = int(time.time())  # Unix timestamp

            logger.info(
                f"✅ Successfully uploaded {len(uint32_data_points)} uint32 values to split '{split_name}'"
            )
            logger.info(f"   📊 Total bits represented: {len(uint32_data_points) * 32}")

        except Exception as e:
            logger.error(f"❌ Failed to upload uint32 data: {e}")
            self.stats["upload_errors"] += 1
            raise

    def _upload_worker(self):
        """Worker thread for high-frequency uploads (every second)"""
        logger.info(
            "⏰ Starting high-frequency upload scheduler (1 second intervals)..."
        )

        while self.running:
            try:
                # Read and accumulate bits into uint32 values
                uint32_data_points = self._read_and_accumulate_bits()

                if uint32_data_points:
                    self._upload_uint32_data(uint32_data_points)
                else:
                    logger.debug("📭 No complete uint32 batches ready for upload")

            except Exception as e:
                logger.error(f"❌ Upload worker error: {e}")

            # Wait for next upload cycle (1 second)
            for _ in range(self.upload_interval):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("🛑 High-frequency upload scheduler stopped")

    def start(self):
        """Start the quantum uploader"""
        if self.running:
            logger.warning("⚠️ Uploader is already running")
            return

        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

        self.running = True

        # Start upload thread
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()

        logger.info("🟢 QuantumUploader started successfully")

    def stop(self):
        """Stop the quantum uploader"""
        if not self.running:
            logger.warning("⚠️ Uploader is not running")
            return

        logger.info("🛑 Stopping QuantumUploader...")
        self.running = False

        # Wait for thread to finish
        if self.upload_thread and self.upload_thread.is_alive():
            thread_timeout = get_config("quantum_uploader.thread_join_timeout")
            self.upload_thread.join(timeout=thread_timeout)

        # Upload any remaining data
        try:
            uint32_data_points = self._read_and_accumulate_bits()
            if uint32_data_points:
                self._upload_uint32_data(uint32_data_points)
        except Exception as e:
            logger.error(f"❌ Error during final upload: {e}")

        logger.info("✅ QuantumUploader stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get uploader status"""
        # Count pending files
        try:
            pattern = os.path.join(self.data_dir, "bits_*.json")
            pending_files = len(glob.glob(pattern))
        except:  # noqa: E722
            pending_files = 0

        # Count bits in accumulator
        with self.accumulator_lock:
            accumulated_bits = len(self.bit_accumulator)

        return {
            "running": self.running,
            "pending_files": pending_files,
            "accumulated_bits": accumulated_bits,
            "bits_needed_for_next_uint32": self.bits_per_upload
            - (accumulated_bits % self.bits_per_upload),
            "stats": self.stats.copy(),
        }

    def print_status(self):
        """Print detailed status information"""
        status = self.get_status()

        print("\n" + "=" * 70)
        print("🌌 QUANTUM UPLOADER STATUS (OPTIMIZED MODE)")
        print("=" * 70)

        print(f"🔄 Running: {'✅ Yes' if status['running'] else '❌ No'}")
        print(f"📂 Pending Files: {status['pending_files']}")
        print(f"🔢 Accumulated Bits: {status['accumulated_bits']}")
        print(
            f"⏳ Bits needed for next uint32: {status['bits_needed_for_next_uint32']}"
        )

        print("\n📈 UPLOADER STATISTICS:")
        stats = status["stats"]
        print(f"   📦 Total uint32 Values Uploaded: {stats['total_uint32_uploaded']:,}")
        print(f"   🔢 Total Bits Uploaded: {stats['total_bits_uploaded']:,}")
        print(f"   📤 Total Uploads: {stats['total_uploads']}")
        print(f"   📄 Total Files Processed: {stats['total_files_processed']}")
        print(f"   ❌ Upload Errors: {stats['upload_errors']}")
        print(f"   📋 File Errors: {stats['file_errors']}")
        print(f"   ⚠️ Incomplete Batches: {stats['incomplete_batches']}")

        # Format last upload time
        if stats["last_upload_time"]:
            last_upload = datetime.fromtimestamp(
                stats["last_upload_time"], timezone.utc
            )
            print(f"   🕐 Last Upload: {last_upload.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print("   🕐 Last Upload: Never")

        print("\n💡 OPTIMIZATION INFO:")
        print("   • 32 quantum bits = 1 uint32 value")
        print(f"   • Upload frequency: Every {self.upload_interval} second(s)")
        print("   • Data format: Unix timestamp + uint32 quantum value")
        print("   • Storage efficiency: ~87.5% reduction vs individual bits")

        print("=" * 70)

    def manual_upload(self):
        """Manually trigger an upload"""
        logger.info("🔄 Manual upload triggered...")
        try:
            uint32_data_points = self._read_and_accumulate_bits()
            if uint32_data_points:
                self._upload_uint32_data(uint32_data_points)
                logger.info("✅ Manual upload completed")
            else:
                logger.info("📭 No complete uint32 batches available for manual upload")
        except Exception as e:
            logger.error(f"❌ Manual upload failed: {e}")

    def get_accumulator_status(self) -> Dict[str, Any]:
        """Get detailed accumulator status for debugging"""
        with self.accumulator_lock:
            return {
                "total_bits_in_accumulator": len(self.bit_accumulator),
                "complete_uint32_batches_ready": len(self.bit_accumulator)
                // self.bits_per_upload,
                "remaining_bits": len(self.bit_accumulator) % self.bits_per_upload,
                "next_uint32_completion_progress": f"{len(self.bit_accumulator) % self.bits_per_upload}/{self.bits_per_upload}",
            }


def main():
    """Main function to run the quantum uploader"""
    uploader = QuantumUploader()

    try:
        uploader.start()

        print("🌌 Quantum Data Uploader (Optimized Mode)")
        print("=" * 60)
        print("📦 Collecting 32 quantum bits → 1 uint32 value every second")
        print("⏰ High-frequency uploads (1 second intervals)")
        print("📊 Unix timestamps for efficient storage")
        print("💡 Press Ctrl+C to stop")
        print("=" * 60)

        # Print status every 30 seconds (more frequent for real-time monitoring)
        status_interval = get_config("quantum_uploader.status_display_interval", 30)

        while True:
            time.sleep(status_interval)
            uploader.print_status()

    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal...")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        uploader.stop()


if __name__ == "__main__":
    main()
