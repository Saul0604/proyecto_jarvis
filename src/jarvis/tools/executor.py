"""Valida argumentos y conserva una clasificación estable de errores."""
import asyncio
import http.client
import logging
import json
import socket
import traceback

from jarvis.domain.messages import ToolCall
from jarvis.domain.tools import ToolResult
from jarvis.tools.errors import ToolError
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.validation import validate_arguments

logger = logging.getLogger(__name__)


def failure(code, message):
    return ToolResult(False, {"error": code, "message": message})


class ToolExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    async def execute(self, call: ToolCall) -> ToolResult:
        tool = self.registry.tools.get(call.name)
        if tool is None:
            return failure("unknown_tool", "Herramienta no habilitada.")
        try:
            validate_arguments(call.arguments, tool.definition.input_schema)
        except ValueError as error:
            return failure("invalid_arguments", str(error))
        try:
            data = await asyncio.to_thread(tool.handler, **call.arguments)
            if not isinstance(data, dict):
                raise TypeError("El resultado debe ser un objeto JSON.")
            json.dumps(data, allow_nan=False)
            return ToolResult(True, data)
        except ToolError as error:
            return failure(error.code, str(error))
        except PermissionError:
            return failure("access_denied", "Acceso fuera de permisos.")
        except FileNotFoundError:
            return failure("not_found", "El recurso solicitado no existe.")
        except TimeoutError:
            return failure("timeout", "El recurso superó el tiempo de espera.")
        except (ConnectionError, socket.gaierror, http.client.HTTPException):
            return failure("network_error", "Falló la comunicación con el recurso.")
        except OSError:
            return failure("io_error", "No se pudo leer el recurso solicitado.")
        except ValueError:
            return failure("resource_error", "El recurso o su formato no es compatible.")
        except Exception as error:
            # Tipo y ubicación, sin argumentos, variables ni texto de la excepción.
            frames = [(frame.name, frame.lineno) for frame in traceback.extract_tb(error.__traceback__)]
            logger.error("tool_failure tool=%s type=%s frames=%s", call.name, type(error).__name__, frames)
            return failure("internal_error", "La herramienta falló internamente; consulta el registro técnico.")
