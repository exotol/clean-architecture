"""Unit tests configuration with DI container setup."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.containers import AppContainer
from app.utils.serializer import ItemSerializer


@pytest.fixture(scope="session", autouse=True)
def setup_di_container() -> AppContainer:
    """Initialize DI container for unit tests."""
    container = AppContainer()
    container.infra_container().config.from_dict({})

    # Mock observability strategies to prevent external connections/hangs
    container.infra_container.logging_strategy.override(MagicMock())
    container.infra_container.tracing_strategy.override(MagicMock())
    container.infra_container.metrics_strategy.override(MagicMock())

    container.wire(packages=["app"])
    return container


@pytest.fixture(scope="session")
def di_container(setup_di_container: AppContainer) -> AppContainer:
    """Return the wired DI container (for tests that need strategy mocks)."""
    return setup_di_container


@pytest.fixture
def mock_serializer() -> MagicMock:
    """Mock serializer for unit tests."""
    serializer = MagicMock(spec=ItemSerializer)
    serializer.serialize.side_effect = lambda x: x  # Pass-through
    return serializer
