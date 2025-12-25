from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceConfig:
    """Configuration for Locust performance tests."""

    # Target Host
    DEFAULT_HOST: str = "http://localhost:8000"

    # Metrics
    METRICS_PORT: int = 8888
    METRICS_SERVICE_NAME: str = "locust"

    # User Behavior
    WAIT_TIME_MIN: int = 1
    WAIT_TIME_MAX: int = 5


config = PerformanceConfig()
