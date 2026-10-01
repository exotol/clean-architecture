from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.domain.entities.agent_tools import ExchangeRate
from app.domain.entities.agent_tools import Location
from app.domain.entities.agent_tools import SearchHit
from app.domain.entities.agent_tools import Weather
from app.infrastructure.gateways.agent_tools import DuckDuckGoSearchGateway
from app.infrastructure.gateways.agent_tools import (
    FrankfurterExchangeRateGateway,
)
from app.infrastructure.gateways.agent_tools import OpenMeteoGeocodingGateway
from app.infrastructure.gateways.agent_tools import OpenMeteoWeatherGateway
from tests.schemas.unit.infrastructure.agent_tools import HttpGatewayEntity
from tests.schemas.unit.infrastructure.agent_tools import HttpGatewayExpected
from tests.schemas.unit.infrastructure.agent_tools import SearchGatewayEntity
from tests.schemas.unit.infrastructure.agent_tools import SearchGatewayExpected


class RecordingTransport(httpx.AsyncBaseTransport):
    """Return one configured response and retain its request."""

    def __init__(
        self,
        payload: object,
        status_code: int,
        *,
        invalid_json: bool = False,
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.invalid_json = invalid_json
        self.request: httpx.Request | None = None

    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        """Record request and return the configured response."""
        self.request = request
        if isinstance(self.payload, bytes):
            return httpx.Response(
                self.status_code,
                content=self.payload,
                request=request,
            )
        if self.invalid_json:
            return httpx.Response(
                self.status_code,
                content=b"not-json",
                request=request,
            )
        return httpx.Response(
            self.status_code,
            json=self.payload,
            request=request,
        )


class FakeSearchClient:
    """Record DDGS text arguments and return fixed data."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self.results = results
        self.query: str | None = None
        self.backend: str | None = None
        self.max_results: int | None = None

    def text(
        self,
        query: str,
        *,
        backend: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Return configured results while recording call arguments."""
        self.query = query
        self.backend = backend
        self.max_results = max_results
        return self.results


class FailingSearchClient:
    """Raise a timeout from the synchronous provider boundary."""

    @staticmethod
    def text(
        query: str,
        *,
        backend: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Simulate provider timeout."""
        del query, backend, max_results
        raise TimeoutError


async def _invoke_http_gateway(
    entity: HttpGatewayEntity,
    client: httpx.AsyncClient,
) -> object:
    """Invoke the gateway selected by a data-driven test case."""
    if entity.gateway == "geocoding":
        gateway = OpenMeteoGeocodingGateway(
            client,
            "https://geo.test",
            timeout_seconds=4.0,
        )
        return await gateway.geocode("Moscow")
    if entity.gateway == "weather":
        weather_gateway = OpenMeteoWeatherGateway(
            client,
            "https://weather.test/",
            timeout_seconds=4.0,
        )
        return await weather_gateway.weather(55.75, 37.62)
    currency_gateway = FrankfurterExchangeRateGateway(
        client,
        "https://currency.test",
        timeout_seconds=4.0,
    )
    return await currency_gateway.exchange_rate("eur", "usd")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            HttpGatewayEntity(
                gateway="geocoding",
                payload={
                    "results": [
                        {
                            "name": "Moscow",
                            "country": "Russia",
                            "latitude": 55.75,
                            "longitude": 37.62,
                            "timezone": "Europe/Moscow",
                            "admin1": "Moscow",
                        },
                    ],
                },
            ),
            HttpGatewayExpected(
                result=(
                    Location(
                        name="Moscow",
                        country="Russia",
                        latitude=55.75,
                        longitude=37.62,
                        timezone="Europe/Moscow",
                        admin1="Moscow",
                    ),
                ),
                path="/v1/search",
                params={"name": "Moscow", "count": "5", "language": "en"},
            ),
            id="geocoding_result",
        ),
        pytest.param(
            HttpGatewayEntity(gateway="geocoding", payload={}),
            HttpGatewayExpected(
                result=(),
                path="/v1/search",
                params={"name": "Moscow", "count": "5", "language": "en"},
            ),
            id="geocoding_empty",
        ),
        pytest.param(
            HttpGatewayEntity(
                gateway="weather",
                payload={
                    "timezone": "Europe/Moscow",
                    "current": {
                        "time": "2026-09-08T12:15",
                        "temperature_2m": 18.4,
                        "apparent_temperature": 17.1,
                        "wind_speed_10m": 9.2,
                        "weather_code": 3,
                    },
                },
            ),
            HttpGatewayExpected(
                result=Weather(
                    temperature_c=18.4,
                    apparent_temperature_c=17.1,
                    wind_speed_kmh=9.2,
                    weather_code=3,
                    observed_at=datetime(
                        2026,
                        9,
                        8,
                        12,
                        15,
                        tzinfo=ZoneInfo("Europe/Moscow"),
                    ),
                    timezone="Europe/Moscow",
                ),
                path="/v1/forecast",
                params={
                    "latitude": "55.75",
                    "longitude": "37.62",
                    "current": (
                        "temperature_2m,apparent_temperature,"
                        "wind_speed_10m,weather_code"
                    ),
                    "timezone": "auto",
                },
            ),
            id="current_weather",
        ),
        pytest.param(
            HttpGatewayEntity(
                gateway="currency",
                payload={
                    "date": "2026-09-08",
                    "base": "EUR",
                    "quote": "USD",
                    "rate": 1.17,
                },
            ),
            HttpGatewayExpected(
                result=ExchangeRate(
                    base="EUR",
                    quote="USD",
                    rate=Decimal("1.17"),
                    date=date(2026, 9, 8),
                ),
                path="/v2/rate/EUR/USD",
            ),
            id="exchange_rate",
        ),
        pytest.param(
            HttpGatewayEntity(
                gateway="currency",
                payload=(
                    b'{"date":"2026-09-08","base":"EUR","quote":"USD",'
                    b'"rate":1.162500000000000001}'
                ),
            ),
            HttpGatewayExpected(
                result=ExchangeRate(
                    base="EUR",
                    quote="USD",
                    rate=Decimal("1.162500000000000001"),
                    date=date(2026, 9, 8),
                ),
                path="/v2/rate/EUR/USD",
            ),
            id="exchange_rate_decimal_precision",
        ),
    ],
)
async def test_http_gateways_validate_and_map_success(
    entity: HttpGatewayEntity,
    expected: HttpGatewayExpected,
) -> None:
    # Arrange
    transport = RecordingTransport(entity.payload, entity.status_code)
    async with httpx.AsyncClient(transport=transport) as client:
        # Act
        result = await _invoke_http_gateway(entity, client)

    # Assert
    assert result == expected.result, (
        f"Expected mapped result {expected.result!r}, got {result!r}"
    )
    assert transport.request is not None, (
        f"Expected an outbound request, got {transport.request!r}"
    )
    assert transport.request.url.path == expected.path, (
        f"Expected path {expected.path!r}, got {transport.request.url.path!r}"
    )
    if expected.params is not None:
        actual_params = dict(transport.request.url.params)
        assert actual_params == expected.params, (
            f"Expected params {expected.params!r}, got {actual_params!r}"
        )
    actual_timeout = set(transport.request.extensions["timeout"].values())
    assert actual_timeout == {4.0}, (
        f"Expected a 4-second request timeout, got {actual_timeout!r}"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            HttpGatewayEntity(
                gateway="geocoding",
                payload={},
                status_code=500,
            ),
            HttpGatewayExpected(
                error_type=InfrastructureError,
                path="/v1/search",
            ),
            id="geocoding_http_status",
        ),
        pytest.param(
            HttpGatewayEntity(
                gateway="geocoding",
                payload={"results": [{"name": "Moscow"}]},
            ),
            HttpGatewayExpected(
                error_type=InfrastructureError,
                path="/v1/search",
            ),
            id="geocoding_missing_fields",
        ),
        pytest.param(
            HttpGatewayEntity(gateway="weather", payload={"timezone": "UTC"}),
            HttpGatewayExpected(
                error_type=InfrastructureError,
                path="/v1/forecast",
            ),
            id="weather_missing_current",
        ),
        pytest.param(
            HttpGatewayEntity(
                gateway="weather",
                payload={
                    "timezone": "UTC",
                    "current": {
                        "time": "invalid-date",
                        "temperature_2m": 1,
                        "apparent_temperature": 1,
                        "wind_speed_10m": 1,
                        "weather_code": 0,
                    },
                },
            ),
            HttpGatewayExpected(
                error_type=InfrastructureError,
                path="/v1/forecast",
            ),
            id="weather_invalid_observation_time",
        ),
        pytest.param(
            HttpGatewayEntity(
                gateway="currency",
                payload={},
                status_code=404,
            ),
            HttpGatewayExpected(
                error_type=BusinessError,
                path="/v2/rate/EUR/USD",
            ),
            id="currency_unsupported_pair",
        ),
        pytest.param(
            HttpGatewayEntity(
                gateway="currency",
                payload={},
                status_code=502,
            ),
            HttpGatewayExpected(
                error_type=InfrastructureError,
                path="/v2/rate/EUR/USD",
            ),
            id="currency_http_status",
        ),
        pytest.param(
            HttpGatewayEntity(
                gateway="currency",
                payload={
                    "date": "invalid",
                    "base": "EUR",
                    "quote": "USD",
                    "rate": "not-a-number",
                },
            ),
            HttpGatewayExpected(
                error_type=InfrastructureError,
                path="/v2/rate/EUR/USD",
            ),
            id="currency_invalid_values",
        ),
    ],
)
async def test_http_gateways_map_provider_failures(
    entity: HttpGatewayEntity,
    expected: HttpGatewayExpected,
) -> None:
    # Arrange
    transport = RecordingTransport(entity.payload, entity.status_code)
    async with httpx.AsyncClient(transport=transport) as client:
        # Act
        with pytest.raises(expected.error_type or AssertionError) as error:
            await _invoke_http_gateway(entity, client)

    # Assert
    assert error.value.__cause__ is not None, (
        f"Expected chained provider error, got {error.value.__cause__!r}"
    )
    assert transport.request is not None, (
        f"Expected an outbound request, got {transport.request!r}"
    )
    assert transport.request.url.path == expected.path, (
        f"Expected path {expected.path!r}, got {transport.request.url.path!r}"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            SearchGatewayEntity(
                query="clean architecture",
                results=[
                    {
                        "title": "Clean Architecture",
                        "href": "https://example.com/clean",
                        "body": "A practical guide",
                    },
                ],
            ),
            SearchGatewayExpected(
                result=(
                    SearchHit(
                        title="Clean Architecture",
                        url="https://example.com/clean",
                        snippet="A practical guide",
                    ),
                ),
                backend="duckduckgo",
                max_results=5,
            ),
            id="single_search_hit",
        ),
        pytest.param(
            SearchGatewayEntity(query="nothing", results=[]),
            SearchGatewayExpected(
                result=(),
                backend="duckduckgo",
                max_results=5,
            ),
            id="empty_search_results",
        ),
    ],
)
async def test_search_uses_duckduckgo_and_maps_results(
    entity: SearchGatewayEntity,
    expected: SearchGatewayExpected,
) -> None:
    # Arrange
    client = FakeSearchClient(entity.results)
    gateway = DuckDuckGoSearchGateway(
        timeout_seconds=8,
        client_factory=Mock(return_value=client),
    )

    # Act
    result = await gateway.search(entity.query)

    # Assert
    assert result == expected.result, (
        f"Expected search results {expected.result!r}, got {result!r}"
    )
    assert client.query == entity.query, (
        f"Expected query {entity.query!r}, got {client.query!r}"
    )
    assert client.backend == expected.backend, (
        f"Expected backend {expected.backend!r}, got {client.backend!r}"
    )
    assert client.max_results == expected.max_results, (
        f"Expected max results {expected.max_results}, "
        f"got {client.max_results}"
    )


@pytest.mark.anyio
async def test_search_maps_timeout_to_infrastructure_error() -> None:
    # Arrange
    gateway = DuckDuckGoSearchGateway(
        timeout_seconds=8,
        client_factory=FailingSearchClient,
    )

    # Act
    with pytest.raises(InfrastructureError) as error:
        await gateway.search("slow query")

    # Assert
    assert isinstance(error.value.__cause__, TimeoutError), (
        f"Expected TimeoutError cause, got {error.value.__cause__!r}"
    )


@pytest.mark.anyio
async def test_search_rejects_invalid_provider_payload() -> None:
    # Arrange
    client = FakeSearchClient(
        [{"title": "Unsafe", "href": "relative/path", "body": "Bad URL"}],
    )
    gateway = DuckDuckGoSearchGateway(
        timeout_seconds=8,
        client_factory=Mock(return_value=client),
    )

    # Act
    with pytest.raises(InfrastructureError) as error:
        await gateway.search("invalid result")

    # Assert
    assert error.value.service_name == "duckduckgo", (
        f"Expected duckduckgo service, got {error.value.service_name!r}"
    )


@pytest.mark.anyio
async def test_http_gateway_maps_invalid_json() -> None:
    # Arrange
    transport = RecordingTransport({}, 200, invalid_json=True)
    async with httpx.AsyncClient(transport=transport) as client:
        gateway = OpenMeteoGeocodingGateway(
            client,
            "https://geo.test",
            timeout_seconds=4.0,
        )

        # Act
        with pytest.raises(InfrastructureError) as error:
            await gateway.geocode("Moscow")

    # Assert
    assert error.value.service_name == "open-meteo-geocoding", (
        "Expected open-meteo-geocoding service, "
        f"got {error.value.service_name!r}"
    )


@pytest.mark.anyio
async def test_currency_rejects_invalid_code_before_request() -> None:
    # Arrange
    transport = RecordingTransport({}, 200)
    async with httpx.AsyncClient(transport=transport) as client:
        gateway = FrankfurterExchangeRateGateway(
            client,
            "https://currency.test",
            timeout_seconds=4.0,
        )

        # Act
        with pytest.raises(BusinessError) as error:
            await gateway.exchange_rate("EUR/USD", "RUB")

    # Assert
    assert transport.request is None, (
        f"Expected no request for an invalid code, got {transport.request!r}"
    )
    assert error.value.status_code == 400, (
        f"Expected business status 400, got {error.value.status_code}"
    )


@pytest.mark.anyio
async def test_currency_rejects_mismatched_provider_pair() -> None:
    # Arrange
    transport = RecordingTransport(
        {
            "date": "2026-09-08",
            "base": "GBP",
            "quote": "USD",
            "rate": 1.17,
        },
        200,
    )
    async with httpx.AsyncClient(transport=transport) as client:
        gateway = FrankfurterExchangeRateGateway(
            client,
            "https://currency.test",
            timeout_seconds=4.0,
        )

        # Act
        with pytest.raises(InfrastructureError) as error:
            await gateway.exchange_rate("EUR", "USD")

    # Assert
    assert error.value.service_name == "frankfurter", (
        f"Expected frankfurter service, got {error.value.service_name!r}"
    )
