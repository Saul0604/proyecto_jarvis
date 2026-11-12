"""Resumen acumulativo, migración y protección de los mensajes originales."""
import asyncio
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jarvis.domain.messages import Message, ModelResponse, Role, FinishReason
from jarvis.domain.providers import ProviderError
from jarvis.memory.summarizer import compact_if_needed
from jarvis.storage.sqlite.conversations import ConversationStore, MemoryConflictError


class SummarizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "memory.sqlite3"
        self.store = ConversationStore(self.path)

    def populate(self, count=20, prompt="Presupuesto 12000 MXN"):
        for index in range(count):
            revision, _, _ = self.store.snapshot("faro")
            self.store.append("faro", revision, f"{index}: {prompt}",
                              ModelResponse(Message(Role.ASSISTANT, "Ok"), "m", "fake"))

    def provider(self, reason=FinishReason.STOP, callback=None):
        class Fake:
            def __init__(self):
                self.requests = []

            async def generate(self, request):
                self.requests.append(request)
                if callback:
                    callback()
                return ModelResponse(Message(Role.ASSISTANT, "Faro: presupuesto 12000 MXN."),
                                     request.model, "fake", reason)
        return Fake()

    def test_threshold_and_keep_recent_six(self):
        self.populate(19)
        fake = self.provider()
        self.assertFalse(asyncio.run(compact_if_needed(self.store, "faro", fake, "m")))
        self.populate(1)
        self.assertTrue(asyncio.run(compact_if_needed(self.store, "faro", fake, "m")))
        self.assertEqual(len(self.store.history("faro")), 6)
        snapshot = ConversationStore(self.path).snapshot("faro")
        self.assertIn("12000", snapshot[1][0].content)
        self.assertEqual(len(snapshot[1]), 13)
        self.assertEqual(snapshot[2], 0)

    def test_accumulates_previous_summary(self):
        self.populate()
        asyncio.run(compact_if_needed(self.store, "faro", self.provider(), "m"))
        self.populate(14, "Nueva decisión")
        fake = self.provider()
        asyncio.run(compact_if_needed(self.store, "faro", fake, "m"))
        payload = json.loads(fake.requests[0].messages[-1].content)
        self.assertIn("12000", payload["resumen_anterior"])
        self.assertIn("Nueva decisión", payload["fragmento"])

    def test_truncated_summary_preserves_history(self):
        self.populate()
        with self.assertRaises(ProviderError):
            asyncio.run(compact_if_needed(self.store, "faro", self.provider(FinishReason.LENGTH), "m"))
        self.assertEqual(len(self.store.history("faro")), 20)
        self.assertEqual(self.store.summary("faro"), "")

    def test_clear_during_summary_does_not_restore_memory(self):
        self.populate()
        fake = self.provider(callback=lambda: self.store.clear("faro"))
        with self.assertRaises(MemoryConflictError):
            asyncio.run(compact_if_needed(self.store, "faro", fake, "m"))
        self.assertEqual(self.store.history("faro"), [])
        self.assertEqual(self.store.summary("faro"), "")

    def test_large_turn_uses_bounded_chunks_and_no_omission(self):
        self.populate(1, "x" * 50000)
        fake = self.provider()
        asyncio.run(compact_if_needed(self.store, "faro", fake, "m"))
        self.assertGreater(len(fake.requests), 1)
        fragments = [json.loads(r.messages[-1].content)["fragmento"] for r in fake.requests]
        self.assertTrue(all(len(fragment) <= 16000 for fragment in fragments))
        self.assertIn("x" * 50000, "".join(fragments))
        self.assertEqual(self.store.history("faro"), [])
        self.assertTrue(self.store.summary("faro"))

    def test_old_database_is_upgraded_without_losing_turns(self):
        path = Path(self.temp.name) / "old.sqlite3"
        with sqlite3.connect(path) as connection:
            connection.executescript("""
                CREATE TABLE memory_sessions(name TEXT PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE memory_turns(id INTEGER PRIMARY KEY, session TEXT, prompt TEXT, reply TEXT,
                                         model TEXT, provider TEXT, created_at TEXT);
                INSERT INTO memory_sessions VALUES ('old', 1);
                INSERT INTO memory_turns VALUES (1, 'old', 'Hola', 'Respuesta', 'm', 'p', 'today');
            """)
        store = ConversationStore(path)
        self.assertEqual(store.history("old")[0]["prompt"], "Hola")
        self.assertEqual(store.summary("old"), "")
        store.clear("old")
        self.assertEqual(store.history("old"), [])
