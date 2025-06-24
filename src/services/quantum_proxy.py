from flask import Flask, request, jsonify
from src.core.quantum_cache import QuantumCache, QuantumDataException
import logging
import json
import os
import threading
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Optional
from src.config.config_loader import get_quantum_proxy_config, get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuantumDataBuffer:
    """
    Thread-safe buffer for collecting quantum bits before writing to files
    """

    def __init__(
        self, data_dir: Optional[str] = None, flush_threshold: Optional[int] = None
    ):
        proxy_config = get_quantum_proxy_config()
        self.data_dir = data_dir or proxy_config["data_dir"]
        self.flush_threshold = flush_threshold or proxy_config["flush_threshold"]
        self.buffer = []
        self.lock = Lock()

        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

        # Start periodic flush thread
        self.flush_thread = threading.Thread(target=self._periodic_flush, daemon=True)
        self.flush_thread.start()
        flush_interval = get_config("quantum_proxy.periodic_flush_interval")
        logger.info(
            f"🔄 Started periodic buffer flush every {flush_interval}s (threshold: {self.flush_threshold})"
        )

    def add_bit(self, bit: int):
        """Add a quantum bit with timestamp to the buffer"""
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        data_point = {"timestamp": timestamp, "bit": bit}

        with self.lock:
            self.buffer.append(data_point)

            # Auto-flush if threshold reached
            if len(self.buffer) >= self.flush_threshold:
                self._flush_buffer()

    def _flush_buffer(self):
        """Internal method to flush buffer to file (must be called with lock held)"""
        if not self.buffer:
            return

        try:
            # Create filename with timestamp
            filename = (
                f"bits_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            )
            filepath = os.path.join(self.data_dir, filename)

            # Write buffer to file
            with open(filepath, "w") as f:
                json.dump(self.buffer, f, indent=4)

            logger.info(f"📝 Flushed {len(self.buffer)} bits to {filename}")
            self.buffer = []

        except Exception as e:
            logger.error(f"❌ Failed to flush buffer: {e}")

    def flush(self):
        """Manually flush buffer to file"""
        with self.lock:
            self._flush_buffer()

    def _periodic_flush(self):
        """Periodically flush buffer (runs in background thread)"""
        flush_interval = get_config("quantum_proxy.periodic_flush_interval")
        while True:
            time.sleep(flush_interval)  # Wait configured seconds
            with self.lock:
                if self.buffer:
                    self._flush_buffer()

    def get_status(self):
        """Get buffer status"""
        with self.lock:
            return {
                "buffer_size": len(self.buffer),
                "flush_threshold": self.flush_threshold,
                "data_dir": self.data_dir,
            }


app = Flask(__name__)

# Initialize quantum data buffer
quantum_buffer = QuantumDataBuffer()

# Initialize quantum cache
try:
    # Use quantum_cache configuration directly
    quantum_cache = QuantumCache()
    logger.info("✅ Quantum cache initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize quantum cache: {e}")
    quantum_cache = None


@app.route("/")
def index():
    """API information"""
    return jsonify(
        {
            "name": "Quantum Random Number Generator",
            "description": "Provides quantum random bits",
            "version": "2.0.0",
            "data_type": "QUANTUM",
            "endpoints": {
                "/bit": "Get single quantum bit",
                "/bits?count=N": "Get N quantum bits",
                "/status": "Get cache status",
                "/stats": "Get statistics",
                "/bit-stats": "Get bit distribution statistics",
            },
        }
    )


@app.route("/bit")
def get_bit():
    """Get single quantum bit"""
    if not quantum_cache:
        return jsonify({"error": "Quantum cache not available", "status": "error"}), 503

    try:
        bit = quantum_cache.get_bit()

        # Add to collection buffer for uploading
        quantum_buffer.add_bit(bit)

        return jsonify({"bit": bit, "data_type": "quantum"})
    except QuantumDataException as e:
        logger.error(f"Quantum data error: {e}")
        return jsonify(
            {
                "error": "Quantum data unavailable",
                "message": str(e),
                "status": "error",
                "data_type": "none",
            }
        ), 503
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify(
            {"error": "Internal server error", "message": str(e), "status": "error"}
        ), 500


@app.route("/bits")
def get_bits():
    """Get multiple quantum bits"""
    if not quantum_cache:
        return jsonify({"error": "Quantum cache not available", "status": "error"}), 503

    try:
        count = int(request.args.get("count", 1))
        max_bits = get_config("quantum_proxy.max_bits_per_request")
        if count <= 0 or count > max_bits:
            return jsonify({"error": f"Invalid count. Must be 1-{max_bits}"}), 400

        bits = quantum_cache.get_bits(count)

        # Add each bit to collection buffer for uploading
        for bit in bits:
            quantum_buffer.add_bit(bit)

        return jsonify({"bits": bits, "count": len(bits), "data_type": "quantum"})
    except QuantumDataException as e:
        logger.error(f"Quantum data error: {e}")
        return jsonify(
            {
                "error": "Quantum data unavailable",
                "message": str(e),
                "status": "error",
                "data_type": "none",
            }
        ), 503
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify(
            {"error": "Internal server error", "message": str(e), "status": "error"}
        ), 500


@app.route("/status")
def get_status():
    """Get quantum cache status"""
    if not quantum_cache:
        return jsonify({"error": "Quantum cache not available", "status": "error"}), 503

    try:
        status = quantum_cache.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/stats")
def get_stats():
    """Get statistics"""
    if not quantum_cache:
        return jsonify({"error": "Quantum cache not available", "status": "error"}), 503

    try:
        stats = quantum_cache.get_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/bit-stats")
def get_bit_stats():
    """Get bit distribution statistics"""
    if not quantum_cache:
        return jsonify({"error": "Quantum cache not available", "status": "error"}), 503

    try:
        bit_stats = quantum_cache.get_bit_stats()
        return jsonify(bit_stats)
    except Exception as e:
        logger.error(f"Error getting bit stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/reset-stats", methods=["POST"])
def reset_stats():
    """Reset statistics"""
    if not quantum_cache:
        return jsonify({"error": "Quantum cache not available", "status": "error"}), 503

    try:
        quantum_cache.reset_stats()
        return jsonify({"message": "Statistics reset successfully"})
    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify(
        {
            "error": "Endpoint not found",
            "available_endpoints": [
                "/bit - Get single quantum bit",
                "/bits?count=N - Get N quantum bits",
                "/status - Get cache status",
                "/stats - Get statistics",
                "/bit-stats - Get bit distribution statistics",
                "/reset-stats - Reset statistics",
            ],
        }
    ), 404


if __name__ == "__main__":
    if quantum_cache:
        logger.info(f"Quantum source: {quantum_cache.quantum_api_url}")

    logger.info("Available endpoints:")
    logger.info("  GET  /bit - Get single quantum bit")
    logger.info("  GET  /bits?count=N - Get N quantum bits")
    logger.info("  GET  /status - Get cache status")
    logger.info("  GET  /stats - Get statistics")
    logger.info("  GET  /bit-stats - Get bit distribution statistics")
    logger.info("  POST /reset-stats - Reset statistics")

    app.run(host="0.0.0.0", port=80, debug=False)
