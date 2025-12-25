from pydantic import BaseModel

from app.presentation.api.schemas.root import HelloWorld


class RootEntity(BaseModel):
    path: str


class RootExpected(BaseModel):
    status_code: int
    json_body: HelloWorld
