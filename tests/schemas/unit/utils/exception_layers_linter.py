"""Schemas for exception layers linter unit tests."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class ExceptionLayersSnippetEntity(BaseModel):
    """Input snippet entity for exception layers check."""

    code: str = Field(description="Python source code snippet to validate")
    file_path: str = Field(
        default="src/app/application/use_case.py",
        description="Simulated file path with layer information",
    )


class ExceptionLayersExpected(BaseModel):
    """Expected outcome for exception layers check."""

    is_valid: bool = Field(
        description="Whether snippet is expected to pass all checks",
    )
    expected_violation_code: str | None = Field(
        default=None,
        description=(
            "Expected violation code (e.g. EXC001, EXC002, EXC003, EXC004)"
        ),
    )
