from pydantic import BaseModel
from pydantic import Field

from app.core.constants import HELLO_WORLD


class HelloWorld(BaseModel):
    message: str | None = Field(HELLO_WORLD, description="Hello World")
