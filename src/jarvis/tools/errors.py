"""Errores públicos de herramientas; sus mensajes no deben incluir secretos."""

class ToolError(ValueError):
    code = "resource_error"

class ToolConfigurationError(ToolError):
    code = "configuration_error"

class ResourceLimitError(ToolError):
    code = "resource_limit"

class NetworkError(ToolError):
    code = "network_error"
