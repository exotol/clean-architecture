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
    AGENT_SERVICE = Event("AGENT_SERVICE", "Agent request execution")
    AGENT_MODEL = Event("AGENT_MODEL", "Agent model invocation")
    AGENT_GEOCODE = Event("AGENT_GEOCODE", "Agent geocoding tool")
    AGENT_WEATHER = Event("AGENT_WEATHER", "Agent weather tool")
    AGENT_CURRENCY = Event("AGENT_CURRENCY", "Agent exchange rate tool")
    AGENT_WEB_SEARCH = Event("AGENT_WEB_SEARCH", "Agent web search tool")
