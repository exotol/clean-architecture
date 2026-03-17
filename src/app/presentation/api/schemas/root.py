from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field

from app.core.constants import HELLO_WORLD


class HelloWorld(BaseModel):
    """Root endpoint response schema."""

    message: str | None = Field(HELLO_WORLD, description="Hello World")
