from __future__ import annotations

from pydantic import BaseModel


class CommitValidationEntity(BaseModel):
    """Commit message input entity for validation."""

    message: str


class CommitValidationExpected(BaseModel):
    """Expected result of commit validation."""

    is_valid: bool
    error_message_substring: str | None = None
