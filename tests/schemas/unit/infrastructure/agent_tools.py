from __future__ import annotations

from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict


class HttpGatewayEntity(BaseModel):
    """Input data for one HTTP gateway scenario."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    gateway: Literal["geocoding", "weather", "currency"]
    payload: object
    status_code: int = 200


class HttpGatewayExpected(BaseModel):
    """Expected output and outbound request for an HTTP gateway scenario."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    result: object | None = None
    error_type: type[Exception] | None = None
    path: str
    params: dict[str, Any] | None = None


class SearchGatewayEntity(BaseModel):
    """Input data for a DuckDuckGo gateway scenario."""

    results: list[dict[str, Any]]
    query: str


class SearchGatewayExpected(BaseModel):
    """Expected DuckDuckGo result and invocation details."""

    result: object
    backend: str
    max_results: int
