from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class Document:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
