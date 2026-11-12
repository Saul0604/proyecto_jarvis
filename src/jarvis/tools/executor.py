"""Valida argumentos y devuelve errores estructurados al agente."""
import asyncio
import http.client

from jarvis.domain.messages import ToolCall
from jarvis.domain.tools import ToolResult
from jarvis.tools.registry import ToolRegistry


def validate_arguments(arguments, schema):
    properties = schema["properties"]
    if set(arguments) - set(properties) or set(schema["required"]) - set(arguments):
        raise ValueError("Argumentos desconocidos o parámetros obligatorios ausentes.")
    for name, value in arguments.items():
        rule = properties[name]
        if rule["type"] == "integer":
            if type(value) is not int or not rule["minimum"] <= value <= rule["maximum"]:
                raise ValueError(f"El argumento {name} debe ser un entero dentro del rango permitido.")
        elif not isinstance(value, str) or not rule["minLength"] <= len(value) <= rule["maxLength"] or not value.strip():
            raise ValueError(f"El argumento {name} debe ser texto válido.")


class ToolExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(self, call: ToolCall) -> ToolResult:
        tool = self.registry.tools.get(call.name)
        if tool is None:
            return ToolResult(False, {"error": "unknown_tool", "message": "Herramienta no habilitada."})
        try:
            validate_arguments(call.arguments, tool.definition.input_schema)
            data = await asyncio.to_thread(tool.handler, **call.arguments)
            return ToolResult(True, data)
        except PermissionError:
            return ToolResult(False, {"error": "access_denied", "message": "Acceso fuera de permisos."})
        except (OSError, http.client.HTTPException):
            return ToolResult(False, {"error": "io_error", "message": "No se pudo leer el recurso solicitado."})
        except (ValueError, LookupError, TypeError, AttributeError):
            return ToolResult(False, {"error": "invalid_request", "message":
                "Revisa argumentos, formato, tamaño del recurso y configuración de la herramienta."})
