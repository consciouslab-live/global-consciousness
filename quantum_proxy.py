from flask import Flask, request, jsonify
from quantum_cache import QuantumCache, QuantumDataException
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize quantum cache
try:
    quantum_cache = QuantumCache(
        cache_size=1024,
        prefetch_threshold=512,
        request_timeout=10,
        max_retries=5,
    )
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
        if count <= 0 or count > 1000:
            return jsonify({"error": "Invalid count. Must be 1-1000"}), 400

        bits = quantum_cache.get_bits(count)
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
