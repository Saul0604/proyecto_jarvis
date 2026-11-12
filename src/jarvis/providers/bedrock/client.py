"""Traduce conversaciones de texto a la API Converse de Bedrock."""

import asyncio

from botocore.exceptions import (
    BotoCoreError, ClientError, ConnectTimeoutError, NoCredentialsError,
    PartialCredentialsError, ReadTimeoutError,
)

from jarvis.domain.messages import FinishReason, Message, ModelResponse, Role, TokenUsage, ToolCall
from jarvis.domain.providers import (
    ModelRequest, ProviderAuthenticationError, ProviderRateLimitError,
    ProviderRequestError, ProviderResponseError, ProviderTimeoutError,
    ProviderUnavailableError,
)


class BedrockProvider:
    def __init__(self, client):
        self._client = client

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Envía el historial y normaliza la respuesta para el agente."""
        system = []
        messages = []
        for message in request.messages:
            if message.role is Role.SYSTEM:
                if messages or not message.content:
                    raise ProviderRequestError("Coloca instrucciones de sistema al inicio.")
                system.append({"text": message.content})
                continue
            if message.role is Role.TOOL:
                role = "user"
                blocks = [{"toolResult": {"toolUseId": message.tool_call_id,
                           "content": [{"text": message.content}]}}]
            else:
                role = message.role.value
                blocks = []
                if message.content and message.content.strip():
                    blocks.append({"text": message.content})
                for call in message.tool_calls:
                    blocks.append({"toolUse": {"toolUseId": call.id,
                                   "name": call.name, "input": call.arguments}})
            if not blocks:
                raise ProviderRequestError("El mensaje necesita texto o llamadas.")
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"].extend(blocks)
            else:
                messages.append({"role": role, "content": blocks})

        if not messages or messages[0]["role"] != "user":
            raise ProviderRequestError("El historial debe empezar con un mensaje de usuario.")

        parameters = {
            "modelId": request.model,
            "messages": messages,
            "inferenceConfig": {"maxTokens": request.max_output_tokens},
        }
        if request.tools:
            parameters["toolConfig"] = {"tools": [
                {"toolSpec": {"name": tool.name, "description": tool.description,
                 "inputSchema": {"json": tool.input_schema}}}
                for tool in request.tools
            ]}
        if system:
            parameters["system"] = system

        try:
            response = await asyncio.to_thread(self._client.converse, **parameters)
        except (NoCredentialsError, PartialCredentialsError):
            raise ProviderAuthenticationError("Configura tus credenciales de AWS.") from None
        except (ConnectTimeoutError, ReadTimeoutError):
            raise ProviderTimeoutError("Bedrock superó el tiempo de espera.") from None
        except ClientError as error:
            code = error.response["Error"]["Code"]
            error_type = {
                "AccessDeniedException": ProviderAuthenticationError,
                "ExpiredTokenException": ProviderAuthenticationError,
                "UnrecognizedClientException": ProviderAuthenticationError,
                "ThrottlingException": ProviderRateLimitError,
                "ServiceQuotaExceededException": ProviderRateLimitError,
                "ModelTimeoutException": ProviderTimeoutError,
                "ValidationException": ProviderRequestError,
                "ResourceNotFoundException": ProviderRequestError,
            }.get(code, ProviderUnavailableError)
            raise error_type(f"Bedrock devolvió {code}. Revisa región, perfil y permisos.") from None
        except BotoCoreError:
            raise ProviderUnavailableError("Falló la comunicación con Bedrock.") from None

        try:
            stop_reason = response["stopReason"]
            reason = {
                "end_turn": FinishReason.STOP,
                "tool_use": FinishReason.TOOL_CALLS,
                "stop_sequence": FinishReason.STOP,
                "max_tokens": FinishReason.LENGTH,
                "model_context_window_exceeded": FinishReason.LENGTH,
                "content_filtered": FinishReason.CONTENT_FILTER,
                "guardrail_intervened": FinishReason.CONTENT_FILTER,
            }.get(stop_reason, FinishReason.UNKNOWN)
            output = response["output"]["message"]
            blocks = output["content"]
            calls = tuple(
                ToolCall(block["toolUse"]["toolUseId"], block["toolUse"]["name"],
                         block["toolUse"]["input"])
                for block in blocks if "toolUse" in block
            )
            content = "\n".join(block["text"] for block in blocks if "text" in block)
            if output["role"] != "assistant" or (not content and not calls and reason is not FinishReason.CONTENT_FILTER):
                raise ProviderResponseError("Bedrock devolvió un mensaje vacío.")
            usage = response.get("usage", {})
            return ModelResponse(
                message=Message(Role.ASSISTANT, content, calls),
                model=request.model,
                provider="bedrock",
                finish_reason=reason,
                usage=TokenUsage(
                    input_tokens=usage.get("inputTokens"),
                    output_tokens=usage.get("outputTokens"),
                ),
                response_id=response.get("ResponseMetadata", {}).get("RequestId"),
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ProviderResponseError("La respuesta de Bedrock tiene un formato inesperado.") from None
