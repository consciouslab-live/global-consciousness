import os
import time
import threading
import logging
import json
import glob
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv
from datasets import Dataset, Features, Value
from huggingface_hub import login

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
    """

    def __init__(
        self,
        hf_repo: str = "consciouslab-live/quantum-bits",
        data_dir: str = "quantum_data",
        upload_interval: int = 600,  # seconds between uploads (10 minutes)
        batch_size: int = 10000,  # maximum bits per upload
    ):
        """
        Initialize quantum uploader

        Args:
            hf_repo: Hugging Face repository name
            data_dir: Directory containing data files from quantum_proxy.py
            upload_interval: Seconds between uploads
            batch_size: Maximum bits to upload in one batch
        """
        self.hf_repo = hf_repo
        self.data_dir = data_dir
        self.upload_interval = upload_interval
        self.batch_size = batch_size

        # Control flags
        self.running = False
        self.upload_thread = None

        # Statistics
        self.stats = {
            "total_bits_uploaded": 0,
            "total_uploads": 0,
            "total_files_processed": 0,
            "last_upload_time": None,
            "upload_errors": 0,
            "file_errors": 0,
        }

        # Login to Hugging Face
        self._login_hf()

        logger.info("🚀 QuantumUploader initialized")
        logger.info(f"   Repository: {self.hf_repo}")
        logger.info(f"   Data Directory: {self.data_dir}")
        logger.info(f"   Upload interval: {self.upload_interval}s")
        logger.info(f"   Batch size: {self.batch_size}")

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

    def _read_data_files(self) -> List[Dict]:
        """Read all available data files"""
        data_points = []
        files_processed = 0

        try:
            # Find all JSON files in data directory
            pattern = os.path.join(self.data_dir, "bits_*.json")
            files = glob.glob(pattern)

            if not files:
                logger.debug(f"📭 No data files found in {self.data_dir}")
                return []

            logger.info(f"📂 Found {len(files)} data files to process")

            for filepath in files:
                try:
                    with open(filepath, "r") as f:
                        file_data = json.load(f)

                    if isinstance(file_data, list):
                        data_points.extend(file_data)
                        files_processed += 1

                        # Remove processed file
                        os.remove(filepath)
                        logger.debug(
                            f"📄 Processed and removed {os.path.basename(filepath)} ({len(file_data)} bits)"
                        )
                    else:
                        logger.warning(f"⚠️ Invalid data format in {filepath}")

                except Exception as e:
                    logger.error(f"❌ Error processing file {filepath}: {e}")
                    self.stats["file_errors"] += 1

            self.stats["total_files_processed"] += files_processed
            logger.info(
                f"✅ Processed {files_processed} files, collected {len(data_points)} bits"
            )

        except Exception as e:
            logger.error(f"❌ Error reading data files: {e}")
            self.stats["file_errors"] += 1

        return data_points

    def _upload_data(self, data_points: List[Dict]):
        """Upload data points to Hugging Face"""
        if not data_points:
            logger.debug("📭 No data to upload")
            return

        try:
            logger.info(
                f"📤 Uploading {len(data_points)} quantum bits to Hugging Face..."
            )

            # Define dataset features
            features = Features({"timestamp": Value("string"), "bit": Value("int8")})

            # Create dataset
            dataset = Dataset.from_list(data_points, features=features)

            # Determine split name (date and hour)
            today = datetime.now(timezone.utc).strftime("bits_%Y%m%d_%H")

            # Upload to Hugging Face
            dataset.push_to_hub(self.hf_repo, split=today)

            # Update statistics
            self.stats["total_uploads"] += 1
            self.stats["total_bits_uploaded"] += len(data_points)
            self.stats["last_upload_time"] = (
                datetime.now(timezone.utc).isoformat() + "Z"
            )

            logger.info(
                f"✅ Successfully uploaded {len(data_points)} bits to split '{today}'"
            )

        except Exception as e:
            logger.error(f"❌ Failed to upload data: {e}")
            self.stats["upload_errors"] += 1
            raise

    def _upload_worker(self):
        """Worker thread for periodic uploads"""
        logger.info("⏰ Starting periodic upload scheduler...")

        while self.running:
            try:
                # Read data files
                data_points = self._read_data_files()

                if data_points:
                    # Split into batches if needed
                    for i in range(0, len(data_points), self.batch_size):
                        batch = data_points[i : i + self.batch_size]
                        self._upload_data(batch)

                        # Small delay between batches
                        if i + self.batch_size < len(data_points):
                            time.sleep(5)

            except Exception as e:
                logger.error(f"❌ Upload worker error: {e}")

            # Wait for next upload cycle
            for _ in range(self.upload_interval):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("🛑 Upload scheduler stopped")

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
            self.upload_thread.join(timeout=10)

        # Upload any remaining data
        try:
            data_points = self._read_data_files()
            if data_points:
                self._upload_data(data_points)
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

        return {
            "running": self.running,
            "pending_files": pending_files,
            "stats": self.stats.copy(),
        }

    def print_status(self):
        """Print detailed status information"""
        status = self.get_status()

        print("\n" + "=" * 60)
        print("🌌 QUANTUM UPLOADER STATUS")
        print("=" * 60)

        print(f"🔄 Running: {'✅ Yes' if status['running'] else '❌ No'}")
        print(f"📂 Pending Files: {status['pending_files']}")

        print("\n📈 UPLOADER STATISTICS:")
        stats = status["stats"]
        print(f"   Total Bits Uploaded: {stats['total_bits_uploaded']:,}")
        print(f"   Total Uploads: {stats['total_uploads']}")
        print(f"   Total Files Processed: {stats['total_files_processed']}")
        print(f"   Upload Errors: {stats['upload_errors']}")
        print(f"   File Errors: {stats['file_errors']}")
        print(f"   Last Upload: {stats['last_upload_time'] or 'Never'}")

        print("=" * 60)

    def manual_upload(self):
        """Manually trigger an upload"""
        logger.info("🔄 Manual upload triggered...")
        try:
            data_points = self._read_data_files()
            if data_points:
                self._upload_data(data_points)
                logger.info("✅ Manual upload completed")
            else:
                logger.info("📭 No data available for manual upload")
        except Exception as e:
            logger.error(f"❌ Manual upload failed: {e}")


def main():
    """Main function to run the quantum uploader"""
    uploader = QuantumUploader()

    try:
        uploader.start()

        print("🌌 Quantum Data Uploader")
        print("=" * 50)
        print("📋 Listening for data files from quantum_proxy.py")
        print("💡 Press Ctrl+C to stop")
        print("=" * 50)

        # Print status every 60 seconds
        while True:
            time.sleep(60)
            uploader.print_status()

    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal...")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        uploader.stop()


if __name__ == "__main__":
    main()
