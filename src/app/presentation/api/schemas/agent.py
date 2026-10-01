from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class AgentRequest(BaseModel):
    """A bounded, stateless user request to the agent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Вопрос агенту: погода, курс валют или веб-поиск",
    )


class AgentResponse(BaseModel):
    """Final answer and executed tool names, without model reasoning."""

    answer: str = Field(..., description="Итоговый ответ агента")
    tools_used: list[str] = Field(
        ...,
        description="Имена выполненных инструментов по порядку",
    )
