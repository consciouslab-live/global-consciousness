import requests
import time
import threading
import logging
import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from scipy.stats import binomtest
import humanize
from src.config.config_loader import get_quantum_cache_config, get_config

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuantumDataException(Exception):
    """Quantum data acquisition exception"""

    pass


class QuantumCache:
    """
    Quantum random number cache class

    Features:
    - Double buffering mechanism: current buffer and preload buffer
    - Prefetching: fetch next batch of data in advance
    - Smart retry: exponential backoff retry strategy
    - Strict: explicit error on failure
    - Data source: quantum random number generator
    """

    def __init__(
        self,
        cache_size: Optional[int] = None,
        prefetch_threshold: Optional[int] = None,
        api_key: Optional[str] = None,
        request_timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initialize quantum cache

        Args:
            cache_size: Amount of data to fetch each time (if None, uses config)
            prefetch_threshold: Start prefetching when remaining data falls below this value (if None, uses config)
            api_key: API key for quantum service (if None, loads from QUANTUM_API_KEY env var)
            request_timeout: Request timeout duration (if None, uses config)
            max_retries: Maximum number of retries (if None, uses config)
        """
        # Load configuration
        cache_config = get_quantum_cache_config()

        self.cache_size = cache_size or cache_config["cache_size"]
        self.prefetch_threshold = (
            prefetch_threshold or cache_config["prefetch_threshold"]
        )
        self.request_timeout = request_timeout or cache_config["request_timeout"]
        self.max_retries = max_retries or cache_config["max_retries"]

        self.quantum_api_url = "https://api.quantumnumbers.anu.edu.au/"

        # Load API key from environment
        self.api_key = api_key or os.getenv("QUANTUM_API_KEY")

        if self.cache_size < self.prefetch_threshold:
            raise QuantumDataException(
                "Cache size must be greater than prefetch threshold"
            )

        if not self.api_key:
            raise QuantumDataException(
                "API key is required. Please set QUANTUM_API_KEY environment variable or pass api_key parameter."
            )

        # Double buffering
        self.current_buffer: List[int] = []
        self.next_buffer: List[int] = []

        # State tracking
        self.current_index = 0
        self.last_fetch_time = 0
        self.is_prefetching = False
        self.fetch_lock = threading.Lock()
        self.prefetch_thread: Optional[threading.Thread] = None

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "prefetch_count": 0,
            "rate_limit_hits": 0,
            "timeout_errors": 0,
            "network_errors": 0,
        }

        # Bit statistics for distribution analysis
        self.bit_stats = {
            "count_0": 0,
            "count_1": 0,
            "total_bits": 0,
        }

        # Record startup time for runtime calculation
        self.startup_time = time.time()

        logger.info(f"🔧 Quantum Cache initialized with API: {self.quantum_api_url}")

        # Initialize cache
        self._initial_load()

    def _get_api_headers(self) -> Dict[str, str]:
        """Get headers for API format"""
        if not self.api_key:
            raise QuantumDataException("API key is required but not set")
        return {"x-api-key": self.api_key}

    def _get_api_params(self) -> Dict[str, Any]:
        """Get parameters for format"""
        return {"length": self.cache_size, "type": "uint8"}

    def _fetch_raw_data(self) -> Optional[List[int]]:
        """
        Fetch raw data from quantum API - absolutely no pseudo-random data used

        Returns:
            Returns quantum data list on success, None on failure
        """
        start_time = time.time()

        headers = self._get_api_headers()
        params = self._get_api_params()

        self.stats["total_requests"] += 1

        # Smart retry mechanism
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Fetching quantum data from ANU Quantum API (attempt {attempt + 1})"
                )

                response = requests.get(
                    self.quantum_api_url,
                    headers=headers,
                    params=params,
                    timeout=self.request_timeout,
                )

                if response.status_code == 200:
                    data = response.json()

                    # Check for success in API format
                    if data.get("success") is True and "data" in data:
                        raw_data = data["data"]
                        # Convert directly to random bits
                        bits = [x % 2 for x in raw_data]

                        self.stats["successful_requests"] += 1
                        elapsed_time = time.time() - start_time
                        logger.info(
                            f"✅ Successfully fetched {len(bits)} quantum bits in {elapsed_time:.2f}s"
                        )
                        return bits
                    else:
                        logger.warning(
                            f"API returned failure: {data.get('message', 'Unknown error')}"
                        )

                elif response.status_code == 429:
                    rate_limit_wait = get_config("quantum_cache.rate_limit_wait")
                    logger.warning(
                        f"Rate limit exceeded, waiting {rate_limit_wait}s..."
                    )
                    self.stats["rate_limit_hits"] += 1
                    time.sleep(rate_limit_wait)  # Wait before retry
                    continue

                elif response.status_code == 401:
                    logger.error("❌ CRITICAL: Invalid API Key")
                    raise QuantumDataException(
                        "Invalid API Key. Please check your QUANTUM_API_KEY."
                    )

                elif response.status_code == 403:
                    logger.error(
                        "❌ CRITICAL: Access forbidden - check API key permissions"
                    )
                    raise QuantumDataException(
                        "Access forbidden. Please check your API key permissions."
                    )

                else:
                    logger.warning(f"HTTP error: {response.status_code}")
                    logger.warning(f"Response: {response.text}")

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                self.stats["timeout_errors"] += 1
            except requests.exceptions.RequestException as e:
                logger.warning(f"Network error (attempt {attempt + 1}): {e}")
                self.stats["network_errors"] += 1
            except Exception as e:
                logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                max_backoff = get_config("quantum_cache.exponential_backoff_max")
                wait_time = min(2**attempt, max_backoff)  # Maximum wait from config
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        # All retries failed
        self.stats["failed_requests"] += 1
        elapsed_time = time.time() - start_time
        logger.error(f"❌ All fetch attempts failed after {elapsed_time:.2f}s")
        return None

    def _initial_load(self):
        """Initial loading of quantum data"""
        logger.info("🚀 Initial quantum data loading...")
        data = self._fetch_raw_data()
        if data:
            self.current_buffer = data
            self.last_fetch_time = time.time()
            logger.info(
                f"✅ Initial load complete: {len(self.current_buffer)} quantum bits loaded"
            )
        else:
            logger.error("❌ CRITICAL: Failed to load initial quantum data")
            self.current_buffer = []
            raise QuantumDataException("Failed to load initial quantum data.")

    def _prefetch_data(self):
        """Prefetch next batch of quantum data in the background"""
        if self.is_prefetching:
            return

        def prefetch_worker():
            self.is_prefetching = True
            self.stats["prefetch_count"] += 1

            try:
                logger.info("🔄 Starting quantum data prefetch...")
                data = self._fetch_raw_data()

                with self.fetch_lock:
                    if data:
                        self.next_buffer = data
                        logger.info(
                            f"✅ Prefetch complete: {len(data)} quantum bits ready"
                        )
                    else:
                        logger.error("❌ Prefetch failed - maintaining current buffer")
                        self.next_buffer = []

            except Exception as e:
                logger.error(f"Prefetch error: {e}")
                with self.fetch_lock:
                    self.next_buffer = []
            finally:
                self.is_prefetching = False

        self.prefetch_thread = threading.Thread(target=prefetch_worker, daemon=True)
        self.prefetch_thread.start()

    def _should_prefetch(self) -> bool:
        """Check if prefetching should be triggered"""
        remaining = len(self.current_buffer) - self.current_index
        return (
            remaining <= self.prefetch_threshold
            and not self.is_prefetching
            and len(self.next_buffer) == 0
        )

    def _should_switch_buffer(self) -> bool:
        """Check if buffer switching should occur"""
        remaining = len(self.current_buffer) - self.current_index
        return remaining <= 0 and len(self.next_buffer) > 0

    def get_bit(self) -> int:
        """
        Get a single quantum bit

        Returns:
            Quantum random bit (0 or 1)

        Raises:
            QuantumDataException: When quantum data is not available
        """
        # Start prefetching if needed
        if self._should_prefetch():
            self._prefetch_data()

        # Switch buffer if needed
        if self._should_switch_buffer():
            with self.fetch_lock:
                self.current_buffer = self.next_buffer[:]
                self.next_buffer = []
                self.current_index = 0
                logger.info(
                    f"🔄 Buffer switched: {len(self.current_buffer)} quantum bits available"
                )

        # Check if we have data
        if self.current_index >= len(self.current_buffer):
            logger.error("❌ CRITICAL: No quantum data available")
            raise QuantumDataException("No quantum data available.")

        # Return quantum bit
        bit = self.current_buffer[self.current_index]
        self.current_index += 1
        self.stats["cache_hits"] += 1

        # Update bit statistics
        if bit == 0:
            self.bit_stats["count_0"] += 1
        else:
            self.bit_stats["count_1"] += 1
        self.bit_stats["total_bits"] += 1

        return bit

    def get_bits(self, count: int) -> List[int]:
        """
        Get multiple quantum bits

        Args:
            count: Number of bits to get

        Returns:
            List of quantum random bits

        Raises:
            QuantumDataException: When quantum data is not available or count > MAX_API_BITS
        """
        if count <= 0:
            return []
        max_api_bits = get_config("quantum_cache.max_api_bits")
        if count > max_api_bits:
            raise QuantumDataException(
                f"Requested bits ({count}) exceed API maximum ({max_api_bits}) per request."
            )
        bits = []
        for _ in range(count):
            bits.append(self.get_bit())

        return bits

    def get_status(self) -> Dict[str, Any]:
        """Get cache status"""
        remaining_bits = len(self.current_buffer) - self.current_index
        next_buffer_bits = len(self.next_buffer)

        return {
            "remaining_bits": remaining_bits,
            "next_buffer_bits": next_buffer_bits,
            "is_prefetching": self.is_prefetching,
            "api_url": self.quantum_api_url,
            "last_fetch_time": self.last_fetch_time,
            "cache_size": self.cache_size,
            "prefetch_threshold": self.prefetch_threshold,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistical information"""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistical counters"""
        for key in self.stats:
            self.stats[key] = 0

        # Reset bit statistics
        self.bit_stats = {
            "count_0": 0,
            "count_1": 0,
            "total_bits": 0,
        }

        logger.info("📊 Statistics reset")

    def get_bit_stats(self) -> Dict[str, Any]:
        """
        Get bit distribution statistics

        Returns:
            Dictionary containing bit statistics including p-value analysis
        """

        sample_size = self.bit_stats["total_bits"]
        count_0 = self.bit_stats["count_0"]
        count_1 = self.bit_stats["count_1"]

        if sample_size == 0:
            return {
                "sample_size": 0,
                "count_0": 0,
                "count_1": 0,
                "ratio_0": 0.0,
                "ratio_1": 0.0,
                "bias": 0.0,
                "p_value": 1.0,
                "significant": False,
            }

        ratio_0 = count_0 / sample_size
        ratio_1 = count_1 / sample_size
        fair_ratio = get_config("quantum_cache.coin_fairness_threshold")
        bias = abs(ratio_0 - fair_ratio)

        # Perform binomial test to check if the distribution significantly deviates from 50/50
        # We test against null hypothesis that p=0.5 (fair coin)
        coin_fairness = get_config("quantum_cache.coin_fairness_threshold")
        significance_level = get_config("quantum_cache.statistical_significance")
        p_value = binomtest(count_1, sample_size, coin_fairness).pvalue
        significant = bool(p_value < significance_level)

        # Calculate runtime using humanize
        current_time = time.time()
        runtime_seconds = int(current_time - self.startup_time)
        runtime_str = humanize.naturaldelta(runtime_seconds)

        return {
            "sample_size": sample_size,
            "count_0": count_0,
            "count_1": count_1,
            "ratio_0": round(ratio_0, 4),
            "ratio_1": round(ratio_1, 4),
            "bias": round(bias, 4),
            "p_value": round(float(p_value), 4),
            "significant": significant,
            "runtime": runtime_str,
            "runtime_seconds": runtime_seconds,
        }
