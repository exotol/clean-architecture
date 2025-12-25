from pydantic import BaseModel


class MetricsEntity(BaseModel):
    path: str
    trigger_path: str


class MetricsExpected(BaseModel):
    status_code: int
    content_type: str
    contains: list[str]
