"""Contrato de proveedores: entrada, salida y errores comunes, sin SDKs.

Los adaptadores concretos traducen ModelRequest a su API y devuelven
ModelResponse. Las claves y conexiones pertenecen al adaptador, no a la
solicitud. El contrato incluye definiciones de herramientas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from jarvis.domain.messages import Message, ModelResponse
from jarvis.domain.tools import ToolDefinition


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """Datos de una generación, incluyendo el contexto que debe ver el modelo.

    `model` es el identificador API del perfil seleccionado. `messages` contiene
    el historial relevante, no solo el último mensaje. El límite de salida es
    una solicitud al proveedor, no una garantía de costo máximo de toda la tarea.
    Las capacidades y límites específicos se validarán en cada adaptador.
    """

    model: str
    messages: tuple[Message, ...]
    max_output_tokens: int = 2048
    tools: tuple[ToolDefinition, ...] = ()

    def __post_init__(self) -> None:
        """Rechaza solicitudes mal formadas antes de intentar acceder a la red."""
        if not isinstance(self.tools, tuple) or not all(isinstance(tool, ToolDefinition) for tool in self.tools):
            raise TypeError("tools debe ser una tupla de ToolDefinition.")
        if len({tool.name for tool in self.tools}) != len(self.tools):
            raise ValueError("Las herramientas deben tener nombres únicos.")
        if not isinstance(self.model, str):
            raise TypeError("model debe ser texto.")
        if not self.model.strip():
            raise ValueError("La solicitud necesita un identificador de modelo.")
        if not isinstance(self.messages, tuple):
            raise TypeError("messages debe ser una tupla de Message.")
        if not self.messages:
            raise ValueError("La solicitud necesita al menos un mensaje.")
        if not all(isinstance(message, Message) for message in self.messages):
            raise TypeError("Cada elemento de messages debe ser un Message.")
        if type(self.max_output_tokens) is not int:
            raise TypeError("max_output_tokens debe ser un entero.")
        if self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens debe ser mayor que cero.")


class ProviderError(Exception):
    """Base para fallos previstos de una integración de modelo.

    El adaptador traduce los errores del SDK a estas excepciones, usando mensajes
    sin claves ni contenido privado. No captura cancelaciones ni oculta errores
    de programación. El agente puede capturar esta base para tratar fallos comunes.
    """


class ProviderAuthenticationError(ProviderError):
    """Credenciales ausentes, inválidas o sin autorización suficiente."""


class ProviderRateLimitError(ProviderError):
    """El proveedor rechazó la consulta por límites de uso o cuota.

    No implica que un reintento inmediato vaya a funcionar.
    """


class ProviderUnavailableError(ProviderError):
    """El servicio no está disponible o falló la conexión."""


class ProviderTimeoutError(ProviderError):
    """La espera de red superó el tiempo permitido por el adaptador.

    No garantiza que el proveedor haya cancelado el trabajo ni su facturación.
    """


class ProviderRequestError(ProviderError):
    """La API rechazó la solicitud: formato, modelo o capacidad incompatible."""


class ProviderResponseError(ProviderError):
    """La respuesta no pudo convertirse al contrato común de Jarvis."""


class ModelProvider(Protocol):
    """Interfaz estructural de cualquier adaptador de modelos.

    No requiere herencia explícita: una implementación con este método y estos
    tipos satisface el contrato para un comprobador estático. Protocol no valida
    automáticamente un objeto en ejecución ni implementa una conexión de red.
    """

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Genera una respuesta o lanza una subclase de ProviderError.

        El adaptador implementará validación de capacidades, traducción al
        protocolo de su API, espera con timeout y normalización del resultado.
        No ejecutará herramientas ni decidirá permisos o cambios de proveedor.
        La cancelación debe propagarse al llamador. Los reintentos y la selección
        de modelos requieren una política explícita fuera de este contrato.
        """
        ...
