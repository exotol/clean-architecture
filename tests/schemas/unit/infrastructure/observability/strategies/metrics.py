from dataclasses import dataclass
from typing import Any

@dataclass
class RecordRequestEntity:
    event_name: str
    duration: float
    status: str
    error_type: str | None

@dataclass
class RecordRequestExpected:
    counter_add_value: int
    counter_attrs: dict[str, Any]
    histogram_record_value: float
    histogram_attrs: dict[str, Any]
