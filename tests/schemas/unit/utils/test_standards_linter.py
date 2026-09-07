"""Schemas for test writing standards linter unit tests."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class StandardsSnippetEntity(BaseModel):
    """Input snippet entity for test writing standards validation."""

    __test__ = False

    code: str = Field(description="Test source code snippet to validate")
    file_path: str = Field(
        default="tests/unit/test_sample.py",
        description="Virtual file path of the test module",
    )


class StandardsExpected(BaseModel):
    """Expected outcome for test writing standards validation."""

    __test__ = False

    is_valid: bool = Field(
        description="Whether test snippet is expected to pass all standards",
    )
    expected_violation_code: str | None = Field(
        default=None,
        description="Expected violation code (e.g. TST001, TST005, TST006)",
    )
