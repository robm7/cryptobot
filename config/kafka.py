from dataclasses import dataclass
from typing import List
import os

@dataclass
class KafkaConfig:
    bootstrap_servers: List[str]
    security_protocol: str = "SASL_SSL"
    sasl_mechanism: str = "SCRAM-SHA-512"
    sasl_username: str = os.getenv("KAFKA_USERNAME")
    sasl_password: str = os.getenv("KAFKA_PASSWORD")
    group_id: str = "cryptobot-data-service"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False

    @classmethod
    def from_env(cls):
        """Create config from environment variables"""
        servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "").split(",")
        return cls(
            bootstrap_servers=servers,
            sasl_username=os.getenv("KAFKA_USERNAME"),
            sasl_password=os.getenv("KAFKA_PASSWORD")
        )

# Topic names
class KafkaTopics:
    RAW_MARKET_DATA = "raw.market-data"
    NORMALIZED_OHLCV = "normalized.ohlcv"
    PROCESSED_INDICATORS = "processed.indicators"