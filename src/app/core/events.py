from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class Event(NamedTuple):
    """Event descriptor used for monitoring/logging."""

    code: str
    description: str


class Events(Enum):
    """Application events for monitoring instrumentation."""

    SEARCH_SERVICE = Event("SEARCH_SERVICE", "Search service execution")
    HEALTHCHECK = Event("HEALTHCHECK", "Healthcheck execution")
