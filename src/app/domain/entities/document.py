from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class Document:
    """Domain document entity.

    Attributes:
        text: Текстовое содержимое документа.
        metadata: Словарь метаданных документа.
    """

    text: str = field(
        metadata={"description": "Текстовое содержимое документа"},
    )
    metadata: dict[str, Any] = field(
        default_factory=dict,
        metadata={"description": "Словарь метаданных документа"},
    )
