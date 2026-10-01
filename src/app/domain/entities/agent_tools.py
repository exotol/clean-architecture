from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from datetime import date
    from datetime import datetime
    from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Location:
    """Geographic location resolved from a human-readable name.

    Attributes:
        name: Provider's display name for the location.
        country: Country containing the location.
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        timezone: IANA timezone name.
        admin1: First-level administrative region, when available.
    """

    name: str = field(metadata={"description": "Location display name"})
    country: str = field(metadata={"description": "Country name"})
    latitude: float = field(metadata={"description": "Latitude in degrees"})
    longitude: float = field(metadata={"description": "Longitude in degrees"})
    timezone: str = field(metadata={"description": "IANA timezone name"})
    admin1: str | None = field(
        default=None,
        metadata={"description": "First-level administrative region"},
    )


@dataclass(frozen=True, slots=True)
class Weather:
    """Current weather at a geographic point.

    Attributes:
        temperature_c: Air temperature in degrees Celsius.
        apparent_temperature_c: Perceived temperature in degrees Celsius.
        wind_speed_kmh: Wind speed in kilometres per hour.
        weather_code: Open-Meteo WMO weather interpretation code.
        observed_at: Provider timestamp for the observation.
        timezone: IANA timezone used for the observation.
    """

    temperature_c: float = field(
        metadata={"description": "Air temperature in degrees Celsius"},
    )
    apparent_temperature_c: float = field(
        metadata={"description": "Perceived temperature in degrees Celsius"},
    )
    wind_speed_kmh: float = field(
        metadata={"description": "Wind speed in kilometres per hour"},
    )
    weather_code: int = field(
        metadata={"description": "WMO weather interpretation code"},
    )
    observed_at: datetime = field(
        metadata={"description": "Observation timestamp"},
    )
    timezone: str = field(metadata={"description": "IANA timezone name"})


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    """Exchange rate for a currency pair on a given date.

    Attributes:
        base: ISO 4217 source currency code.
        quote: ISO 4217 target currency code.
        rate: Units of quote currency for one unit of base currency.
        date: Date on which the provider published the rate.
    """

    base: str = field(metadata={"description": "Source currency code"})
    quote: str = field(metadata={"description": "Target currency code"})
    rate: Decimal = field(metadata={"description": "Currency exchange rate"})
    date: date = field(metadata={"description": "Published rate date"})


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One result returned by a web search provider.

    Attributes:
        title: Human-readable result title.
        url: Absolute URL of the result.
        snippet: Provider summary of the result page.
    """

    title: str = field(metadata={"description": "Search result title"})
    url: str = field(metadata={"description": "Search result URL"})
    snippet: str = field(metadata={"description": "Search result summary"})
