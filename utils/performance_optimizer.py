"""
Performance Optimizer

This module initializes and configures all performance optimization components
based on the configuration file.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from utils.query_optimizer import (
    set_slow_query_threshold,
    optimize_database
)
from utils.cache_manager import (
    initialize_redis,
    DEFAULT_CACHE_TTL,
    DEFAULT_CACHE_PREFIX
)
from utils.rate_limiter import (
    register_rate_limit,
    register_async_rate_limit,
    adaptive_rate_limit
)
from utils.memory_optimizer import (
    enable_memory_monitoring,
    enable_tracemalloc,
    set_memory_warning_threshold,
    set_memory_critical_threshold
)
from utils.performance_monitor import (
    enable_performance_monitoring,
    set_performance_warning_threshold,
    set_performance_critical_threshold
)

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration file path
DEFAULT_CONFIG_PATH = "config/performance_config.json"

# Global configuration
config = {}

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load performance optimization configuration.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    global config
    
    # Use default path if not provided
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    
    # Check if file exists
    if not os.path.exists(config_path):
        logger.warning(f"Configuration file not found: {config_path}")
        return {}
    
    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Loaded performance configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

def apply_profile(profile_name: str) -> bool:
    """
    Apply a performance optimization profile.
    
    Args:
        profile_name: Profile name
        
    Returns:
        True if successful, False otherwise
    """
    global config
    
    # Check if profile exists
    if "optimization_profiles" not in config or profile_name not in config["optimization_profiles"]:
        logger.error(f"Profile not found: {profile_name}")
        return False
    
    # Get profile
    profile = config["optimization_profiles"][profile_name]
    
    # Apply profile to each component
    for component, settings in profile.items():
        if component in config:
            # Update component settings with profile settings
            config[component].update(settings)
    
    # Re-initialize components with new settings
    initialize_components()
    
    logger.info(f"Applied performance optimization profile: {profile_name}")
    return True

def initialize_components() -> None:
    """Initialize all performance optimization components."""
    # Initialize query optimizer
    initialize_query_optimizer()
    
    # Initialize cache manager
    initialize_cache_manager()
    
    # Initialize rate limiter
    initialize_rate_limiter()
    
    # Initialize memory optimizer
    initialize_memory_optimizer()
    
    # Initialize performance monitor
    initialize_performance_monitor()
    
    logger.info("Initialized all performance optimization components")

def initialize_query_optimizer() -> None:
    """Initialize query optimizer."""
    if "query_optimizer" not in config:
        logger.warning("Query optimizer configuration not found")
        return
    
    query_config = config["query_optimizer"]
    
    # Check if enabled
    if not query_config.get("enabled", True):
        logger.info("Query optimizer is disabled")
        return
    
    # Set slow query threshold
    if "slow_query_threshold" in query_config:
        set_slow_query_threshold(query_config["slow_query_threshold"])
    
    logger.info("Initialized query optimizer")

def initialize_cache_manager() -> None:
    """Initialize cache manager."""
    if "cache_manager" not in config:
        logger.warning("Cache manager configuration not found")
        return
    
    cache_config = config["cache_manager"]
    
    # Check if enabled
    if not cache_config.get("enabled", True):
        logger.info("Cache manager is disabled")
        return
    
    # Initialize Redis
    if "redis" in cache_config:
        redis_config = cache_config["redis"]
        initialize_redis(
            host=redis_config.get("host", "localhost"),
            port=redis_config.get("port", 6379),
            db=redis_config.get("db", 0),
            password=redis_config.get("password"),
            ssl=redis_config.get("ssl", False)
        )
    
    # Set default TTL
    global DEFAULT_CACHE_TTL
    if "default_ttl" in cache_config:
        DEFAULT_CACHE_TTL = cache_config["default_ttl"]
    
    # Set cache prefix
    global DEFAULT_CACHE_PREFIX
    if "cache_prefix" in cache_config:
        DEFAULT_CACHE_PREFIX = cache_config["cache_prefix"]
    
    logger.info("Initialized cache manager")

def initialize_rate_limiter() -> None:
    """Initialize rate limiter."""
    if "rate_limiter" not in config:
        logger.warning("Rate limiter configuration not found")
        return
    
    rate_config = config["rate_limiter"]
    
    # Check if enabled
    if not rate_config.get("enabled", True):
        logger.info("Rate limiter is disabled")
        return
    
    # Register exchange limits
    if "exchange_limits" in rate_config:
        for exchange, limits in rate_config["exchange_limits"].items():
            if limits.get("adaptive", False):
                adaptive_rate_limit(
                    service=exchange,
                    initial_rate=limits.get("requests_per_second", 1.0),
                    burst_size=limits.get("burst_size", 1)
                )
            else:
                register_rate_limit(
                    service=exchange,
                    requests_per_second=limits.get("requests_per_second", 1.0),
                    burst_size=limits.get("burst_size", 1)
                )
                register_async_rate_limit(
                    service=exchange,
                    requests_per_second=limits.get("requests_per_second", 1.0),
                    burst_size=limits.get("burst_size", 1)
                )
    
    # Register API limits
    if "api_limits" in rate_config:
        for api, limits in rate_config["api_limits"].items():
            if limits.get("adaptive", False):
                adaptive_rate_limit(
                    service=api,
                    initial_rate=limits.get("requests_per_second", 5.0),
                    burst_size=limits.get("burst_size", 10)
                )
            else:
                register_rate_limit(
                    service=api,
                    requests_per_second=limits.get("requests_per_second", 5.0),
                    burst_size=limits.get("burst_size", 10)
                )
                register_async_rate_limit(
                    service=api,
                    requests_per_second=limits.get("requests_per_second", 5.0),
                    burst_size=limits.get("burst_size", 10)
                )
    
    logger.info("Initialized rate limiter")

def initialize_memory_optimizer() -> None:
    """Initialize memory optimizer."""
    if "memory_optimizer" not in config:
        logger.warning("Memory optimizer configuration not found")
        return
    
    memory_config = config["memory_optimizer"]
    
    # Check if enabled
    if not memory_config.get("enabled", True):
        logger.info("Memory optimizer is disabled")
        return
    
    # Enable memory monitoring
    if "monitoring" in memory_config and memory_config["monitoring"].get("enabled", True):
        monitoring_config = memory_config["monitoring"]
        enable_memory_monitoring(interval=monitoring_config.get("interval", 60))
        
        # Set thresholds
        if "warning_threshold" in monitoring_config:
            set_memory_warning_threshold(monitoring_config["warning_threshold"])
        
        if "critical_threshold" in monitoring_config:
            set_memory_critical_threshold(monitoring_config["critical_threshold"])
    
    # Enable tracemalloc
    if "tracemalloc" in memory_config and memory_config["tracemalloc"].get("enabled", True):
        tracemalloc_config = memory_config["tracemalloc"]
        enable_tracemalloc(nframes=tracemalloc_config.get("nframes", 25))
    
    logger.info("Initialized memory optimizer")

def initialize_performance_monitor() -> None:
    """Initialize performance monitor."""
    if "performance_monitor" not in config:
        logger.warning("Performance monitor configuration not found")
        return
    
    perf_config = config["performance_monitor"]
    
    # Check if enabled
    if not perf_config.get("enabled", True):
        logger.info("Performance monitor is disabled")
        return
    
    # Enable performance monitoring
    if "monitoring" in perf_config and perf_config["monitoring"].get("enabled", True):
        monitoring_config = perf_config["monitoring"]
        enable_performance_monitoring(interval=monitoring_config.get("interval", 60))
    
    # Set thresholds
    if "thresholds" in perf_config:
        thresholds_config = perf_config["thresholds"]
        
        if "warning" in thresholds_config:
            set_performance_warning_threshold(thresholds_config["warning"])
        
        if "critical" in thresholds_config:
            set_performance_critical_threshold(thresholds_config["critical"])
    
    logger.info("Initialized performance monitor")

def optimize_all(session=None) -> Dict[str, Any]:
    """
    Run all optimization tasks.
    
    Args:
        session: Database session (optional)
        
    Returns:
        Optimization results
    """
    results = {}
    
    # Optimize database
    if session is not None:
        try:
            results["database"] = optimize_database(session)
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
            results["database"] = {"error": str(e)}
    
    # Add more optimization tasks here
    
    return results

def initialize(config_path: Optional[str] = None, profile: Optional[str] = None) -> bool:
    """
    Initialize performance optimization.
    
    Args:
        config_path: Path to configuration file
        profile: Performance optimization profile to apply
        
    Returns:
        True if successful, False otherwise
    """
    # Load configuration
    if not load_config(config_path):
        return False
    
    # Apply profile if specified
    if profile is not None:
        if not apply_profile(profile):
            return False
    else:
        # Initialize components with default settings
        initialize_components()
    
    return True

def get_config() -> Dict[str, Any]:
    """
    Get current configuration.
    
    Returns:
        Configuration dictionary
    """
    return config

def update_config(new_config: Dict[str, Any]) -> bool:
    """
    Update configuration.
    
    Args:
        new_config: New configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    global config
    
    # Update configuration
    config.update(new_config)
    
    # Re-initialize components
    initialize_components()
    
    return True

def save_config(config_path: Optional[str] = None) -> bool:
    """
    Save configuration to file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        True if successful, False otherwise
    """
    global config
    
    # Use default path if not provided
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    
    # Save configuration
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved performance configuration to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False

# Initialize on module import if config file exists
if os.path.exists(DEFAULT_CONFIG_PATH):
    initialize()