"""Mensajes de dominio independientes de las APIs de los proveedores.

Los adaptadores traducen estas estructuras al protocolo de cada modelo.
Este contrato inicial admite texto y herramientas; no representa todavía
imágenes, audio, streaming ni bloques internos de razonamiento del proveedor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias


JSONValue: TypeAlias = (
    str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
)


class Role(str, Enum):
    """Autor o función de un mensaje dentro de la conversación."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(str, Enum):
    """Motivo normalizado por el que el proveedor terminó la generación."""

    STOP = "stop"
    TOOL_CALLS = "tool_calls"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Solicitud del modelo; no implica autorización ni ejecuta la herramienta.

    El adaptador debe decodificar los argumentos JSON antes de construirla.
    El ejecutor validará después el esquema y los permisos de la herramienta.
    """

    id: str
    name: str
    arguments: dict[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("La llamada necesita un identificador y un nombre.")
        if not isinstance(self.arguments, dict):
            raise TypeError("Los argumentos deben ser un objeto JSON decodificado.")


@dataclass(frozen=True, slots=True)
class Message:
    """Unidad de conversación de texto, con llamadas o resultado de herramienta.

    Un mensaje TOOL lleva el identificador de la llamada que está respondiendo.
    Su contenido es texto: un resultado estructurado puede serializarse como JSON.
    Solo ASSISTANT puede solicitar herramientas, incluso sin texto acompañante.

    `frozen` evita reasignar campos, pero no congela diccionarios anidados:
    los consumidores no deben modificar los argumentos después de entregarlos.
    """

    role: Role
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.role, Role):
            raise TypeError("Usa un valor de Role para indicar el autor.")
        if self.content is not None and not isinstance(self.content, str):
            raise TypeError("El contenido debe ser texto o None.")
        if not isinstance(self.tool_calls, tuple) or not all(
            isinstance(call, ToolCall) for call in self.tool_calls
        ):
            raise TypeError("tool_calls debe ser una tupla de ToolCall.")
        if self.tool_calls and self.role is not Role.ASSISTANT:
            raise ValueError("Solo el asistente puede solicitar herramientas.")
        identifiers = [call.id for call in self.tool_calls]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Los identificadores de llamadas deben ser únicos.")
        if self.role is Role.TOOL:
            if not self.tool_call_id or not self.tool_call_id.strip():
                raise ValueError("El resultado necesita el identificador de su llamada.")
            if self.content is None:
                raise ValueError("El resultado de herramienta necesita contenido.")
        elif self.tool_call_id is not None:
            raise ValueError("Solo un resultado de herramienta lleva tool_call_id.")
        if self.content is None and not self.tool_calls:
            raise ValueError("El mensaje necesita contenido o llamadas a herramientas.")


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Consumo informado por el proveedor; None significa que no se informó.

    Los tokens cacheados y de razonamiento son subconjuntos, cuando así los
    reporte el proveedor. No se suman de nuevo al total de entrada y salida.
    No representa un precio: las tarifas pertenecen a otra capa.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None

    def __post_init__(self) -> None:
        for value in (
            self.input_tokens,
            self.output_tokens,
            self.cached_input_tokens,
            self.reasoning_tokens,
        ):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("El consumo debe ser un entero no negativo o None.")
        for subset, total in (
            (self.cached_input_tokens, self.input_tokens),
            (self.reasoning_tokens, self.output_tokens),
        ):
            if subset is not None and total is not None and subset > total:
                raise ValueError("Un subconjunto de tokens no puede superar su total.")

    @property
    def total_tokens(self) -> int | None:
        """Total conocido; no confunde información ausente con consumo cero."""
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Respuesta normalizada de una generación, no de la tarea completa.

    Los errores de transporte o autenticación se tratarán en el adaptador,
    sin convertirlos en mensajes correctos del asistente.
    """

    message: Message
    model: str
    provider: str
    finish_reason: FinishReason = FinishReason.UNKNOWN
    usage: TokenUsage = field(default_factory=TokenUsage)
    response_id: str | None = None

    def __post_init__(self) -> None:
        if self.message.role is not Role.ASSISTANT:
            raise ValueError("La respuesta del modelo debe contener un mensaje ASSISTANT.")
        if not self.model.strip() or not self.provider.strip():
            raise ValueError("La respuesta debe identificar el modelo y el proveedor.")
        if not isinstance(self.finish_reason, FinishReason):
            raise TypeError("Usa un valor de FinishReason.")
        if self.finish_reason is FinishReason.TOOL_CALLS and not self.message.tool_calls:
            raise ValueError("La finalización TOOL_CALLS necesita llamadas a herramientas.")
