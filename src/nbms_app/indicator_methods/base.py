from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MethodContext:
    indicator: Any
    profile: Any
    user: Any
    params: dict[str, Any]


@dataclass
class MethodResult:
    status: str
    output: dict[str, Any]
    error_message: str = ""


class BaseIndicatorMethod:
    key = "base"

    def run(self, context: MethodContext) -> MethodResult:  # pragma: no cover - interface
        raise NotImplementedError
