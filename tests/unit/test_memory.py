"""Persistencia, contexto y confirmación de turnos."""
import asyncio
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from jarvis.domain.messages import Message, ModelResponse, Role, FinishReason
from jarvis.domain.providers import ProviderUnavailableError
from jarvis.memory.session import ConversationSession
from jarvis.storage.sqlite.conversations import ConversationStore, MemoryConflictError
from jarvis.tools.registry import build_tools
from jarvis.interfaces.cli.app import main


class FakeProvider:
    def __init__(self):
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return ModelResponse(Message(Role.ASSISTANT, "Respuesta"), request.model, "fake", FinishReason.STOP)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "memory.sqlite3"
        self.store = ConversationStore(self.path)
        self.provider = FakeProvider()

    def session(self, name="faro", store=None):
        return ConversationSession(self.provider, "test", build_tools(), store or self.store, name)

    def test_reopen_and_model_change_preserve_context(self):
        asyncio.run(self.session().ask("Presupuesto: 12000"))
        reopened = ConversationStore(self.path)
        session = ConversationSession(self.provider, "other-model", build_tools(), reopened, "faro")
        asyncio.run(session.ask("Gasté 3500"))
        request = self.provider.requests[-1]
        self.assertEqual(request.model, "other-model")
        self.assertEqual([m.content for m in request.messages[1:]],
                         ["Presupuesto: 12000", "Respuesta", "Gasté 3500"])
        self.assertEqual(len(reopened.history("faro")), 2)

    def test_sessions_are_isolated_and_clear_removes_context(self):
        asyncio.run(self.session().ask("Dato privado"))
        asyncio.run(self.session("otra").ask("Hola"))
        self.assertEqual(len(self.provider.requests[-1].messages), 2)
        self.store.clear("faro")
        self.assertEqual(self.store.history("faro"), [])
        self.assertEqual(len(self.store.history("otra")), 1)

    def test_failed_turn_does_not_pollute_memory(self):
        class FailingProvider:
            async def generate(self, request):
                raise ProviderUnavailableError("offline")
        session = ConversationSession(FailingProvider(), "test", build_tools(), self.store, "faro")
        with self.assertRaises(ProviderUnavailableError):
            asyncio.run(session.ask("Hola"))
        self.assertEqual(self.store.history("faro"), [])

    def test_cancellation_does_not_save_partial_turn(self):
        class CancelledProvider:
            async def generate(self, request):
                raise asyncio.CancelledError()
        session = ConversationSession(CancelledProvider(), "test", build_tools(), self.store, "faro")
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(session.ask("Hola"))
        self.assertEqual(self.store.history("faro"), [])

    def test_concurrent_change_and_clear_invalidate_snapshot(self):
        revision, _, _ = self.store.snapshot("faro")
        response = ModelResponse(Message(Role.ASSISTANT, "Ok"), "test", "fake")
        self.store.append("faro", revision, "Uno", response)
        with self.assertRaises(MemoryConflictError):
            self.store.append("faro", revision, "Dos", response)
        revision, _, _ = self.store.snapshot("faro")
        self.store.clear("faro")
        with self.assertRaises(MemoryConflictError):
            self.store.append("faro", revision, "Tres", response)
        self.assertEqual(self.store.history("faro"), [])

    def test_context_is_compacted_automatically(self):
        for index in range(22):
            asyncio.run(self.session().ask(str(index)))
        _, messages, omitted = self.store.snapshot("faro")
        self.assertEqual(len(messages), 17)
        self.assertEqual(omitted, 0)
        self.assertEqual(len(self.store.history("faro")), 8)
        self.assertEqual(self.store.summary("faro"), "Respuesta")

    def test_cli_interactive_and_management(self):
        arguments = ["jarvis", "--db", str(self.path), "--session", "chat"]
        with patch("sys.argv", arguments), patch(
            "jarvis.interfaces.cli.app.build_provider", return_value=(self.provider, "test")
        ), patch("builtins.input", side_effect=["Hola", "Recuerda", "/salir"]), redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 0)
        self.assertEqual(len(self.store.history("chat")), 2)
        with patch("sys.argv", arguments + ["--clear-memory"]), patch(
            "jarvis.interfaces.cli.app.build_provider", side_effect=AssertionError("No consultar API")
        ), redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 0)
        self.assertEqual(self.store.history("chat"), [])

    def test_no_memory_does_not_create_database(self):
        path = Path(self.temp.name) / "unused.sqlite3"
        with patch("sys.argv", ["jarvis", "--db", str(path), "--no-memory", "Hola"]), patch(
            "jarvis.interfaces.cli.app.build_provider", return_value=(self.provider, "test")
        ), redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 0)
        self.assertFalse(path.exists())
