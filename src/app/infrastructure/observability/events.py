from enum import Enum
from typing import NamedTuple


class Event(NamedTuple):
    code: str
    description: str


class Events(Enum):
    SEARCH_SERVICE = Event("SEARCH_SRV", "Search service execution")
