"""Schemas for core exceptions unit tests."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class AppErrorEntity(BaseModel):
    """Input parameters for constructing an error instance."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    error_class_name: str = Field(
        description="Name of exception class to instantiate",
    )
    detail: str | None = Field(
        default=None,
        description="Optional explicit error detail",
    )
    kwargs: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional keyword arguments for constructor",
    )


class AppErrorExpected(BaseModel):
    """Expected properties of constructed error instance."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    status_code: int = Field(description="Expected HTTP status code")
    code: str = Field(description="Expected error code string")
    title: str = Field(description="Expected error title")
    detail: str = Field(description="Expected error detail message")
    urn_type_error: str = Field(description="Expected URN type error string")
    invalid_params: list[dict[str, str]] | None = Field(
        default=None,
        description="Expected invalid params list or None",
    )
