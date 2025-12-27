"""Unit tests configuration with DI container setup."""

from unittest.mock import MagicMock

import pytest

from app.core.containers import AppContainer
from app.utils.configs import load_settings
from app.utils.serializer import ItemSerializer


@pytest.fixture(scope="session", autouse=True)
def setup_di_container() -> None:
    """Initialize DI container for unit tests."""
    container = AppContainer()
    container.infra_container().config.from_dict(load_settings().as_dict())
    container.wire(packages=["app"])


@pytest.fixture
def mock_serializer() -> MagicMock:
    """Mock serializer for unit tests."""
    serializer = MagicMock(spec=ItemSerializer)
    serializer.serialize.side_effect = lambda x: x  # Pass-through
    return serializer
