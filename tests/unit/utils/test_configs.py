"""Unit tests for config loading."""

from __future__ import annotations

from dynaconf import Dynaconf

from app.utils.configs import load_settings


def test_load_settings_returns_dynaconf() -> None:
    # Arrange

    # Act
    settings = load_settings()

    # Assert
    assert isinstance(settings, Dynaconf), (
        f"Expected load_settings() to return Dynaconf instance, "
        f"got {type(settings)}"
    )
