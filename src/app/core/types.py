"""Shared type protocols for DI and runtime interfaces."""

from __future__ import annotations

from typing import Any
from typing import Protocol


class ConfigFromDict(Protocol):
    """Protocol for DI config provider with from_dict (runtime)."""

    def from_dict(self, d: dict[str, Any]) -> None:
        """Load configuration from a dictionary."""
        ...
