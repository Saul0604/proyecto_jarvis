"""Definición común de herramientas y resultados."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    data: dict[str, Any]

    def as_dict(self):
        return {"ok": self.ok, "data": self.data}
