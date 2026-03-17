from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LogStartEntity:
    event_name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    use_log_args: bool
    named_args: dict[str, Any] | None = None


@dataclass
class LogStartExpected:
    bind_called: bool
    args_in_bind: bool
    kwargs_in_bind: bool
    event_in_bind: str
    info_called_with: str
    named_keys: list[str] | None = None  # when set, context has these keys


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
    event_message: str
    exc_info_is_exc: bool
