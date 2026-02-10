from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ExceptionHandlerEntity(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    exception: Exception
    handler_name: str
    request_url: str = "http://testserver/resource"
    headers: dict[str, str] = Field(default_factory=dict)


class ExceptionHandlerExpected(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status_code: int
    content_type_error: str  # Check urn_type_error (in content) or type
    content_title: str
    content_reason: str
    log_level: str | None = None  # "WARNING", "ERROR" or None to not check
