"""Unit tests for config loading."""

from __future__ import annotations

from dynaconf import Dynaconf

from app.utils.configs import load_settings


def test_load_settings_returns_dynaconf() -> None:
    """load_settings() returns a Dynaconf instance."""
    settings = load_settings()
    assert isinstance(settings, Dynaconf)
