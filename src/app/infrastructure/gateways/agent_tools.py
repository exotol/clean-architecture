from __future__ import annotations

import asyncio
import datetime
import decimal
from functools import partial
import json
import re
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

from ddgs import DDGS
from ddgs.exceptions import DDGSException
import httpx
from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import ValidationError

from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.domain.entities.agent_tools import ExchangeRate
from app.domain.entities.agent_tools import Location
from app.domain.entities.agent_tools import SearchHit
from app.domain.entities.agent_tools import Weather
from app.domain.interfaces.agent_tools import IExchangeRateGateway
from app.domain.interfaces.agent_tools import IGeocodingGateway
from app.domain.interfaces.agent_tools import IWeatherGateway
from app.domain.interfaces.agent_tools import IWebSearchGateway


if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence


class _GeocodingItem(BaseModel):
    """Validated Open-Meteo geocoding result."""

    name: str = Field(description="Location display name")
    country: str = Field(description="Country name")
    latitude: float = Field(
        ge=-90,
        le=90,
        allow_inf_nan=False,
        description="Latitude in decimal degrees",
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        allow_inf_nan=False,
        description="Longitude in decimal degrees",
    )
    timezone: str = Field(description="IANA timezone name")
    admin1: str | None = Field(
        default=None,
        description="First-level administrative region",
    )


class _GeocodingPayload(BaseModel):
    """Validated Open-Meteo geocoding response."""

    results: list[_GeocodingItem] = Field(
        default_factory=list,
        description="Matching locations",
    )


class _CurrentWeather(BaseModel):
    """Validated current section of an Open-Meteo weather response."""

    time: datetime.datetime = Field(
        description="ISO 8601 observation timestamp",
    )
    temperature_2m: float = Field(
        allow_inf_nan=False,
        description="Air temperature",
    )
    apparent_temperature: float = Field(
        allow_inf_nan=False,
        description="Perceived temperature",
    )
    wind_speed_10m: float = Field(
        ge=0,
        allow_inf_nan=False,
        description="Wind speed at ten metres",
    )
    weather_code: int = Field(description="WMO weather code")


class _WeatherPayload(BaseModel):
    """Validated Open-Meteo current weather response."""

    timezone: str = Field(description="IANA timezone name")
    current: _CurrentWeather = Field(description="Current observation")


class _ExchangeRatePayload(BaseModel):
    """Validated Frankfurter v2 rate response."""

    date: str = Field(description="Rate publication date")
    base: str = Field(description="Source currency code")
    quote: str = Field(description="Target currency code")
    rate: decimal.Decimal = Field(
        gt=0,
        allow_inf_nan=False,
        description="Units of quote for one base unit",
    )


class _RawSearchItem(BaseModel):
    """Validated raw DDGS text search result."""

    title: str = Field(description="Result title")
    href: HttpUrl = Field(description="Absolute result URL")
    body: str = Field(description="Result summary")


class _TextSearchClient(Protocol):
    """Minimal synchronous DDGS surface used by the adapter."""

    def text(
        self,
        query: str,
        *,
        backend: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Run a text search."""


def _infrastructure_error(service_name: str) -> InfrastructureError:
    """Build a provider-safe infrastructure error."""
    return InfrastructureError(
        f"{service_name} provider request failed",
        service_name=service_name,
    )


def _validated_json[PayloadT: BaseModel](
    response: httpx.Response,
    model: type[PayloadT],
) -> PayloadT:
    """Validate an HTTP JSON body against its boundary schema."""
    response.raise_for_status()
    return model.model_validate(response.json(parse_float=decimal.Decimal))


def _normalize_currency(value: str) -> str:
    """Validate and normalize one ISO 4217-style currency code."""
    if re.fullmatch(r"[A-Za-z]{3}", value) is None:
        message = "Currency code must contain exactly three letters"
        raise BusinessError(message)
    return value.upper()


class OpenMeteoGeocodingGateway(IGeocodingGateway):
    """Open-Meteo implementation of the geocoding port."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        *,
        timeout_seconds: float,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def geocode(self, city: str) -> tuple[Location, ...]:
        """Resolve up to five city candidates through Open-Meteo."""
        try:
            response = await self._client.get(
                f"{self._base_url}/v1/search",
                params={"name": city, "count": 5, "language": "en"},
                timeout=self._timeout_seconds,
            )
            payload = _validated_json(response, _GeocodingPayload)
        except (httpx.HTTPError, json.JSONDecodeError, ValidationError) as exc:
            raise _infrastructure_error("open-meteo-geocoding") from exc
        return tuple(
            Location(
                name=item.name,
                country=item.country,
                latitude=item.latitude,
                longitude=item.longitude,
                timezone=item.timezone,
                admin1=item.admin1,
            )
            for item in payload.results
        )


class OpenMeteoWeatherGateway(IWeatherGateway):
    """Open-Meteo implementation of the current weather port."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        *,
        timeout_seconds: float,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def weather(self, latitude: float, longitude: float) -> Weather:
        """Read current weather through Open-Meteo."""
        try:
            response = await self._client.get(
                f"{self._base_url}/v1/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": (
                        "temperature_2m,apparent_temperature,"
                        "wind_speed_10m,weather_code"
                    ),
                    "timezone": "auto",
                },
                timeout=self._timeout_seconds,
            )
            payload = _validated_json(response, _WeatherPayload)
            return Weather(
                temperature_c=payload.current.temperature_2m,
                apparent_temperature_c=payload.current.apparent_temperature,
                wind_speed_kmh=payload.current.wind_speed_10m,
                weather_code=payload.current.weather_code,
                observed_at=payload.current.time.replace(
                    tzinfo=ZoneInfo(payload.timezone),
                ),
                timezone=payload.timezone,
            )
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            ValidationError,
            ZoneInfoNotFoundError,
        ) as exc:
            raise _infrastructure_error("open-meteo-weather") from exc


class FrankfurterExchangeRateGateway(IExchangeRateGateway):
    """Frankfurter v2 implementation of the exchange-rate port."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        *,
        timeout_seconds: float,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def exchange_rate(self, base: str, quote: str) -> ExchangeRate:
        """Read the latest rate for an ISO 4217 currency pair."""
        normalized_base = _normalize_currency(base)
        normalized_quote = _normalize_currency(quote)
        try:
            response = await self._client.get(
                (
                    f"{self._base_url}/v2/rate/"
                    f"{normalized_base}/{normalized_quote}"
                ),
                timeout=self._timeout_seconds,
            )
            payload = _validated_json(response, _ExchangeRatePayload)
            if (
                payload.base != normalized_base
                or payload.quote != normalized_quote
            ):
                message = "Currency provider returned a different pair"
                raise InfrastructureError(
                    message,
                    service_name="frankfurter",
                )
            return ExchangeRate(
                base=payload.base,
                quote=payload.quote,
                rate=payload.rate,
                date=datetime.date.fromisoformat(payload.date),
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == httpx.codes.NOT_FOUND:
                message = "Currency pair is not supported"
                raise BusinessError(message) from exc
            raise _infrastructure_error("frankfurter") from exc
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            ValueError,
            ValidationError,
        ) as exc:
            raise _infrastructure_error("frankfurter") from exc


class DuckDuckGoSearchGateway(IWebSearchGateway):
    """DDGS implementation of the web-search port."""

    def __init__(
        self,
        *,
        timeout_seconds: int,
        max_results: int = 5,
        client_factory: Callable[[], _TextSearchClient] | None = None,
    ) -> None:
        self._client_factory = client_factory or partial(
            DDGS,
            timeout=timeout_seconds,
        )
        self._max_results = max_results

    async def search(self, query: str) -> tuple[SearchHit, ...]:
        """Search DuckDuckGo without blocking the event loop."""
        try:
            raw_results: Sequence[dict[str, Any]] = await asyncio.to_thread(
                self._search_sync,
                query,
            )
            payloads = tuple(
                _RawSearchItem.model_validate(item)
                for item in raw_results[: self._max_results]
            )
        except (
            DDGSException,
            TimeoutError,
            OSError,
            ValidationError,
        ) as exc:
            raise _infrastructure_error("duckduckgo") from exc
        return tuple(
            SearchHit(
                title=item.title[:300],
                url=str(item.href),
                snippet=item.body[:1500],
            )
            for item in payloads
        )

    def _search_sync(self, query: str) -> list[dict[str, Any]]:
        """Keep provider state local to a worker even after cancellation."""
        client = self._client_factory()
        return client.text(
            query,
            backend="duckduckgo",
            max_results=self._max_results,
        )
