"""Schemas for code cleanliness linter unit tests."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class CleanlinessSnippetEntity(BaseModel):
    """Input snippet entity for code cleanliness checks."""

    code: str = Field(description="Python source code snippet to validate")
    file_path: str = Field(
        default="<test>",
        description="Virtual file path for snippet validation",
    )


class CleanlinessExpected(BaseModel):
    """Expected outcome for code cleanliness check."""

    is_valid: bool = Field(
        description="Whether the code snippet is expected to pass all checks",
    )
    expected_violation_code: str | None = Field(
        default=None,
        description="Expected violation code (e.g. CLN001, CLN002, CLN004)",
    )
