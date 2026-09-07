"""Schemas for model and dataclass description linters unit tests."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class LinterSnippetEntity(BaseModel):
    """Input Python source code snippet to be validated by linter."""

    code: str = Field(..., description="Исходный код Python для анализа")


class LinterExpected(BaseModel):
    """Expected outcome of linter analysis."""

    is_valid: bool = Field(
        ...,
        description="Флаг отсутствия нарушений в анализируемом коде",
    )
    violations_count: int = Field(
        default=0,
        description="Ожидаемое количество найденных нарушений",
    )
    first_violating_field: str | None = Field(
        default=None,
        description="Имя первого поля с нарушением правила",
    )
    error_code: str | None = Field(
        default=None,
        description="Ожидаемый код ошибки линтера (например, BM001 или DC001)",
    )
