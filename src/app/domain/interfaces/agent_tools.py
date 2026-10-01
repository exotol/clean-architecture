from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.domain.entities.agent_tools import ExchangeRate
    from app.domain.entities.agent_tools import Location
    from app.domain.entities.agent_tools import SearchHit
    from app.domain.entities.agent_tools import Weather


class IGeocodingGateway(ABC):
    """Port for resolving city names into geographic locations."""

    @abstractmethod
    async def geocode(self, city: str) -> tuple[Location, ...]:
        """Return matching locations for a city name."""


class IWeatherGateway(ABC):
    """Port for reading current weather at a geographic point."""

    @abstractmethod
    async def weather(self, latitude: float, longitude: float) -> Weather:
        """Return current weather for the supplied coordinates."""


class IExchangeRateGateway(ABC):
    """Port for reading the latest rate for a currency pair."""

    @abstractmethod
    async def exchange_rate(self, base: str, quote: str) -> ExchangeRate:
        """Return the latest exchange rate for the currency pair."""


class IWebSearchGateway(ABC):
    """Port for searching publicly indexed web pages."""

    @abstractmethod
    async def search(self, query: str) -> tuple[SearchHit, ...]:
        """Return web search hits for a query."""
