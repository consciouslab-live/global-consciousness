"""
Configuration loader for Global Consciousness Quantum Data project
Centralized configuration management using YAML
"""

import yaml
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration loader and manager"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self.load_config()

    def load_config(self, config_path: str = "config.yaml"):
        """Load configuration from YAML file"""
        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Configuration file {config_path} not found")

            with open(config_path, "r", encoding="utf-8") as file:
                self._config = yaml.safe_load(file)

            logger.info(f"✅ Configuration loaded from {config_path}")

        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            # Fallback to default configuration
            self._config = self._get_default_config()
            logger.warning("⚠️ Using default configuration values")

    def _get_default_config(self) -> Dict[str, Any]:
        """Fallback default configuration"""
        return {
            "quantum_cache": {
                "cache_size": 1024,
                "prefetch_threshold": 512,
                "request_timeout": 10,
                "max_retries": 5,
                "max_api_bits": 1024,
                "rate_limit_wait": 60,
                "exponential_backoff_max": 60,
                "statistical_significance": 0.05,
                "coin_fairness_threshold": 0.5,
            },
            "quantum_proxy": {
                "data_dir": "quantum_data",
                "flush_threshold": 100,
                "periodic_flush_interval": 60,
                "max_bits_per_request": 1000,
            },
            "quantum_uploader": {
                "hf_repo": "consciouslab-live/quantum-bits",
                "data_dir": "quantum_data",
                "upload_interval": 3600,
                "batch_size": 10000,
                "small_batch_size": 1000,
                "inter_batch_delay": 5,
                "thread_join_timeout": 10,
                "status_display_interval": 60,
            },
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key_path: Configuration key path (e.g., 'quantum_cache.cache_size')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            if default is not None:
                return default
            raise KeyError(f"Configuration key '{key_path}' not found")

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self.get(section, {})

    def reload(self, config_path: str = "config.yaml"):
        """Reload configuration from file"""
        self.load_config(config_path)

    @property
    def quantum_cache(self) -> Dict[str, Any]:
        """Get quantum cache configuration"""
        return self.get_section("quantum_cache")

    @property
    def quantum_proxy(self) -> Dict[str, Any]:
        """Get quantum proxy configuration"""
        return self.get_section("quantum_proxy")

    @property
    def quantum_uploader(self) -> Dict[str, Any]:
        """Get quantum uploader configuration"""
        return self.get_section("quantum_uploader")


# Global configuration instance
config = Config()


# Convenience functions for common access patterns
def get_config(key_path: str, default: Any = None) -> Any:
    """Get configuration value using dot notation"""
    return config.get(key_path, default)


def get_quantum_cache_config() -> Dict[str, Any]:
    """Get quantum cache configuration"""
    return config.quantum_cache


def get_quantum_proxy_config() -> Dict[str, Any]:
    """Get quantum proxy configuration"""
    return config.quantum_proxy


def get_quantum_uploader_config() -> Dict[str, Any]:
    """Get quantum uploader configuration"""
    return config.quantum_uploader
