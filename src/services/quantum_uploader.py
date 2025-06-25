import os
import time
import threading
import logging
import json
import glob
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from datasets import Dataset, Features, Value
from huggingface_hub import login
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
    """

    def __init__(
        self,
        hf_repo: Optional[str] = None,
        data_dir: Optional[str] = None,
        upload_interval: Optional[int] = None,  # seconds between uploads
        batch_size: Optional[int] = None,  # maximum bits per upload
    ):
        """
        Initialize quantum uploader

        Args:
            hf_repo: Hugging Face repository name (if None, uses config)
            data_dir: Directory containing data files from quantum_proxy.py (if None, uses config)
            upload_interval: Seconds between uploads (if None, uses config)
            batch_size: Maximum bits to upload in one batch (if None, uses config)
        """
        # Load configuration
        uploader_config = get_quantum_uploader_config()

        self.hf_repo = hf_repo or uploader_config["hf_repo"]
        self.data_dir = data_dir or uploader_config["data_dir"]
        self.upload_interval = upload_interval or uploader_config["upload_interval"]
        self.batch_size = batch_size or uploader_config["batch_size"]

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

    def _read_data_files(self) -> List[Tuple[str, List[Dict]]]:
        """Read all available data files without deleting them"""
        file_data_pairs = []
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
                        file_data_pairs.append((filepath, file_data))
                        files_processed += 1

                        logger.debug(
                            f"📄 Read {os.path.basename(filepath)} ({len(file_data)} bits)"
                        )
                    else:
                        logger.warning(f"⚠️ Invalid data format in {filepath}")

                except Exception as e:
                    logger.error(f"❌ Error processing file {filepath}: {e}")
                    self.stats["file_errors"] += 1

            total_bits = sum(len(data) for _, data in file_data_pairs)
            logger.info(f"✅ Read {files_processed} files, collected {total_bits} bits")

        except Exception as e:
            logger.error(f"❌ Error reading data files: {e}")
            self.stats["file_errors"] += 1

        return file_data_pairs

    def _upload_data(self, file_data_pairs: List[Tuple[str, List[Dict]]]):
        """Upload data points to Hugging Face and delete files after successful upload"""
        if not file_data_pairs:
            logger.debug("📭 No data to upload")
            return

        # Collect all data points from all files
        all_data_points = []
        for filepath, data_points in file_data_pairs:
            all_data_points.extend(data_points)

        if not all_data_points:
            logger.debug("📭 No data points to upload")
            return

        try:
            logger.info(
                f"📤 Uploading {len(all_data_points)} quantum bits to Hugging Face..."
            )

            # Define dataset features
            features = Features({"timestamp": Value("string"), "bit": Value("int8")})

            # Create dataset
            dataset = Dataset.from_list(all_data_points, features=features)

            # Determine split name (date and hour)
            today = datetime.now(timezone.utc).strftime("bits_%Y%m%d_%H")

            # Upload to Hugging Face
            dataset.push_to_hub(self.hf_repo, split=today)

            # ✅ Only delete files AFTER successful upload
            files_deleted = 0
            for filepath, data_points in file_data_pairs:
                try:
                    os.remove(filepath)
                    files_deleted += 1
                    logger.debug(
                        f"📄 Deleted {os.path.basename(filepath)} after successful upload"
                    )
                except Exception as e:
                    logger.error(f"❌ Failed to delete {filepath}: {e}")

            # Update statistics
            self.stats["total_uploads"] += 1
            self.stats["total_bits_uploaded"] += len(all_data_points)
            self.stats["total_files_processed"] += files_deleted
            self.stats["last_upload_time"] = (
                datetime.now(timezone.utc).isoformat() + "Z"
            )

            logger.info(
                f"✅ Successfully uploaded {len(all_data_points)} bits to split '{today}', deleted {files_deleted} files"
            )

        except Exception as e:
            logger.error(f"❌ Failed to upload data: {e}")
            logger.info("🔒 Files preserved due to upload failure - data is safe!")
            self.stats["upload_errors"] += 1
            raise

    def _upload_worker(self):
        """Worker thread for periodic uploads"""
        logger.info("⏰ Starting periodic upload scheduler...")

        while self.running:
            try:
                # Read data files
                file_data_pairs = self._read_data_files()

                if file_data_pairs:
                    # Calculate total data points for batching
                    total_points = sum(len(data) for _, data in file_data_pairs)

                    if total_points <= self.batch_size:
                        # Upload all files in one batch
                        self._upload_data(file_data_pairs)
                    else:
                        # Split into batches by collecting data points until batch_size is reached
                        current_batch = []
                        current_batch_size = 0

                        for filepath, data_points in file_data_pairs:
                            if current_batch_size + len(data_points) <= self.batch_size:
                                # Add entire file to current batch
                                current_batch.append((filepath, data_points))
                                current_batch_size += len(data_points)
                            else:
                                # Upload current batch if it has data
                                if current_batch:
                                    self._upload_data(current_batch)

                                    # Small delay between batches
                                    inter_batch_delay = get_config(
                                        "quantum_uploader.inter_batch_delay"
                                    )
                                    time.sleep(inter_batch_delay)

                                # Start new batch with current file
                                current_batch = [(filepath, data_points)]
                                current_batch_size = len(data_points)

                        # Upload remaining batch
                        if current_batch:
                            self._upload_data(current_batch)

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
            thread_timeout = get_config("quantum_uploader.thread_join_timeout")
            self.upload_thread.join(timeout=thread_timeout)

        # Upload any remaining data
        try:
            file_data_pairs = self._read_data_files()
            if file_data_pairs:
                self._upload_data(file_data_pairs)
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
            file_data_pairs = self._read_data_files()
            if file_data_pairs:
                self._upload_data(file_data_pairs)
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
