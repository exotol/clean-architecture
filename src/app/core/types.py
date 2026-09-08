"""Shared type interfaces for DI and runtime."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any


class ConfigFromDict(ABC):
    """Interface for DI config provider with from_dict (runtime)."""

    @abstractmethod
    def from_dict(self, d: dict[str, Any]) -> None:
        """Load configuration from a dictionary."""
