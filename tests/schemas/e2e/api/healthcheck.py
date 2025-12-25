from pydantic import BaseModel
from pydantic import Field

from app.presentation.api.schemas.healthcheck import Healthcheck


class HealthcheckEntity(BaseModel):
    path: str


class HealthcheckExpected(BaseModel):
    status_code: int
    json_body: Healthcheck = Field(default_factory=Healthcheck)
