"""Small local script to verify JSON log field renaming (structlog + OTel)."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
import structlog

from app.infrastructure.observability.logging import setup_logging
from app.utils.configs import LoggerConfig
from app.utils.configs import LogLevel
from app.utils.configs import OTLPConfig


def main() -> None:
    """Run OTel + structlog setup and log one line."""
    trace.set_tracer_provider(TracerProvider())
    config = LoggerConfig(
        level=LogLevel.INFO,
        format="%(message)s",
        path=None,
        rotation="1 day",
        retention="1 week",
        loggers_to_root=[],
    )
    otlp = OTLPConfig(
        enabled=False,
        endpoint="",
        service_name="verify_rename",
        insecure=True,
    )
    setup_logging(config, otlp)

    log = structlog.get_logger("test_rename")
    log.info("Test message", key="value")


if __name__ == "__main__":
    main()
