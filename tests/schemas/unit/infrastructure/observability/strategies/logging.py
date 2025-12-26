from dataclasses import dataclass
from typing import Any

@dataclass
class LogStartEntity:
    event_name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    use_log_args: bool

@dataclass
class LogStartExpected:
    bind_called: bool
    args_in_bind: bool
    kwargs_in_bind: bool
    event_in_bind: str
    info_called_with: str

@dataclass
class LogSuccessEntity:
    event_name: str
    result: Any
    use_log_result: bool

@dataclass
class LogSuccessExpected:
    bind_called: bool
    result_in_bind: bool
    info_called_with: str

@dataclass
class LogErrorEntity:
    event_name: str
    exc: Exception

@dataclass
class LogErrorExpected:
    exception_called_with: str
