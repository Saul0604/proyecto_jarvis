"""Pruebas del contrato sin claves, dependencias externas ni acceso a red."""

import asyncio
import unittest

from jarvis.domain.messages import Message, ModelResponse, Role
from jarvis.domain.providers import (
    ModelProvider,
    ModelRequest,
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class RequestTests(unittest.TestCase):
    def test_request_preserves_conversation(self):
        messages = (
            Message(Role.SYSTEM, "Responde en español."),
            Message(Role.USER, "Hola"),
        )
        request = ModelRequest("deepseek-flash", messages)
        self.assertEqual(request.messages, messages)
        self.assertEqual(request.max_output_tokens, 2048)

    def test_invalid_requests(self):
        messages = (Message(Role.USER, "Hola"),)
        cases = (
            ({"model": None, "messages": messages}, TypeError),
            ({"model": "  ", "messages": messages}, ValueError),
            ({"model": "m", "messages": []}, TypeError),
            ({"model": "m", "messages": ()}, ValueError),
            ({"model": "m", "messages": ("Hola",)}, TypeError),
            ({"model": "m", "messages": messages, "max_output_tokens": True}, TypeError),
            ({"model": "m", "messages": messages, "max_output_tokens": 0}, ValueError),
            ({"model": "m", "messages": messages, "max_output_tokens": -1}, ValueError),
        )
        for arguments, error in cases:
            with self.subTest(arguments=arguments), self.assertRaises(error):
                ModelRequest(**arguments)

    def test_adapters_share_contract_without_inheritance(self):
        class FakeProvider:
            async def generate(self, request: ModelRequest) -> ModelResponse:
                return ModelResponse(
                    message=Message(Role.ASSISTANT, "Hola"),
                    model=request.model,
                    provider="fake",
                )

        provider: ModelProvider = FakeProvider()
        response = asyncio.run(provider.generate(ModelRequest(
            "test-model", (Message(Role.USER, "Hola"),),
        )))
        self.assertEqual(response.model, "test-model")
        self.assertEqual(response.message.content, "Hola")

    def test_errors_share_a_common_base(self):
        errors = (
            ProviderAuthenticationError, ProviderRateLimitError,
            ProviderUnavailableError, ProviderTimeoutError,
            ProviderRequestError, ProviderResponseError,
        )
        for error in errors:
            with self.subTest(error=error), self.assertRaises(ProviderError):
                raise error("Fallo de ejemplo sin datos privados")


if __name__ == "__main__":
    unittest.main()
