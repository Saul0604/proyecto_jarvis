"""Regresiones de límites, errores, esquemas y recuperación persistente."""
import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.agent.runner import run_task, TaskIncompleteError
from jarvis.agent.context import bounded_result, request_size
from jarvis.config.settings import AgentSettings, load_settings
from jarvis.domain.messages import Message, ModelResponse, Role, ToolCall, TokenUsage, FinishReason
from jarvis.domain.providers import ProviderError
from jarvis.domain.tools import ToolResult
from jarvis.memory.session import ConversationSession
from jarvis.storage.sqlite.conversations import ConversationStore
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.registry import ToolRegistry, build_tools


class ReliabilityTests(unittest.TestCase):
    def test_nested_schema_and_boolean(self):
        registry = ToolRegistry()
        registry.add("check", "Check", {"enabled": {"type": "boolean"}, "items": {
            "type": "array", "items": {"type": "object", "properties": {"n": {"type": "number"}},
            "required": ["n"], "additionalProperties": False}}}, ["enabled"], lambda **args: args)
        result = asyncio.run(ToolExecutor(registry).execute(ToolCall("1", "check", {"enabled": True, "items": [{"n": 1.5}]})))
        self.assertTrue(result.ok)
        result = asyncio.run(ToolExecutor(registry).execute(ToolCall("1", "check", {"enabled": "true"})))
        self.assertEqual(result.data["error"], "invalid_arguments")

    def test_bad_schema_rejected_at_registration(self):
        registry = ToolRegistry()
        for properties, required in [({}, ["missing"]), ({"x": {"type": "unknown"}}, []),
                                      ({"x": {"type": "string", "$ref": "https://example.com"}}, [])]:
            with self.assertRaises(ValueError):
                registry.add("bad", "Bad", properties, required, lambda: {})
        self.assertFalse(registry.tools)

    def test_internal_failure_is_safe_and_cancellation_propagates(self):
        registry = ToolRegistry()
        def fail():
            raise RuntimeError("SECRET")
        registry.add("fail", "Fail", {}, [], fail)
        with self.assertLogs("jarvis.tools.executor", level="ERROR") as logs:
            result = asyncio.run(ToolExecutor(registry).execute(ToolCall("1", "fail")))
        self.assertEqual(result.data["error"], "internal_error")
        self.assertNotIn("SECRET", str(result) + str(logs.output))
        async def cancel(*args, **kwargs):
            raise asyncio.CancelledError()
        with patch("asyncio.to_thread", cancel), self.assertRaises(asyncio.CancelledError):
            asyncio.run(ToolExecutor(registry).execute(ToolCall("1", "fail")))

    def test_missing_configuration_has_specific_error(self):
        with patch.dict("os.environ", {}, clear=True):
            result = asyncio.run(ToolExecutor(build_tools(web=True)).execute(ToolCall("1", "search_web", {"query": "test"})))
        self.assertEqual(result.data["error"], "configuration_error")

    def test_final_tool_result_is_given_to_model(self):
        registry = ToolRegistry()
        calls = []
        registry.add("read", "Read", {}, [], lambda: calls.append(1) or {"answer": 42})
        requests = []
        class Provider:
            async def generate(self, request):
                requests.append(request)
                if len(requests) == 1:
                    return ModelResponse(Message(Role.ASSISTANT, tool_calls=(ToolCall("1", "read"),)), "m", "fake")
                assert any(m.role is Role.TOOL and "42" in m.content for m in request.messages)
                return ModelResponse(Message(Role.ASSISTANT, "42"), "m", "fake")
        response = asyncio.run(run_task(Provider(), "m", "Read", registry, max_steps=1))
        self.assertEqual(response.message.content, "42")
        self.assertEqual(calls, [1])
        self.assertEqual(len(requests), 2)

    def test_no_execution_after_tool_budget(self):
        calls = []
        registry = ToolRegistry()
        registry.add("read", "Read", {}, [], lambda: calls.append(1) or {})
        class Provider:
            async def generate(self, request):
                return ModelResponse(Message(Role.ASSISTANT, tool_calls=(ToolCall("1", "read"),)), "m", "fake")
        with self.assertRaises(TaskIncompleteError) as caught:
            asyncio.run(run_task(Provider(), "m", "Read", registry, max_steps=1))
        self.assertEqual(len(caught.exception.executed_calls), 1)
        self.assertEqual(calls, [1])

    def test_json_truncation_is_bounded(self):
        text = bounded_result(ToolResult(True, {"value": '\\"' * 10000}), 500)
        self.assertLessEqual(len(text), 500)
        self.assertTrue(json.loads(text)["truncated"])

    def test_context_includes_schemas_and_rejects_oversized_prompt(self):
        class Provider:
            async def generate(self, request):
                raise AssertionError("No enviar solicitudes demasiado grandes")
        with self.assertRaises(ProviderError):
            asyncio.run(run_task(Provider(), "m", "x" * 10000, build_tools(),
                                 settings=AgentSettings(max_request_characters=4000)))

    def test_recent_context_remains_coherent(self):
        requests = []
        class Provider:
            async def generate(self, request):
                requests.append(request)
                return ModelResponse(Message(Role.ASSISTANT, "OK"), "m", "fake")
        history = (Message(Role.USER, "x" * 5000), Message(Role.ASSISTANT, "old"),
                   Message(Role.USER, "recent"), Message(Role.ASSISTANT, "yes"))
        asyncio.run(run_task(Provider(), "m", "now", build_tools(), history=history,
                             settings=AgentSettings(max_request_characters=4000)))
        self.assertLessEqual(request_size(requests[0]), 4000)
        self.assertEqual([m.content for m in requests[0].messages[1:]], ["recent", "yes", "now"])

    def test_summary_failure_recovers_and_usage_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.db"
            store = ConversationStore(path)
            for i in range(20):
                revision, _, _ = store.snapshot("s")
                store.append("s", revision, str(i), ModelResponse(Message(Role.ASSISTANT, "ok"), "m", "fake"))
            class Provider:
                async def generate(self, request):
                    if "Resume la memoria" in request.messages[0].content:
                        raise ProviderError("offline")
                    return ModelResponse(Message(Role.ASSISTANT, "ok"), "m", "fake", FinishReason.STOP, TokenUsage(12, 3))
            session = ConversationSession(Provider(), "m", build_tools(), store, "s")
            asyncio.run(session.ask("nuevo"))
            self.assertEqual(len(store.history("s")), 21)
            self.assertTrue(session.warnings)
            rows = ConversationStore(path).usage("s")
            self.assertEqual([r["phase"] for r in rows], ["summary", "agent"])
            self.assertEqual(rows[-1]["input_tokens"], 12)
            self.assertIsNone(rows[0]["input_tokens"])
            self.assertEqual(rows[0]["task_id"], rows[1]["task_id"])

    def test_settings_reject_unknown_and_boolean_limits(self):
        with self.assertRaises(ValueError):
            AgentSettings(max_steps=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"agent":{"unknown":1}}')
            with self.assertRaises(ValueError):
                load_settings(path)
            path.write_text('{"agent":{"max_steps":1}}')
            self.assertEqual(load_settings(path).max_steps, 1)

    def test_cancel_wait_does_not_claim_to_stop_worker(self):
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        registry = ToolRegistry()
        def handler():
            started.set()
            release.wait(2)
            finished.set()
            return {}
        registry.add("slow", "Slow", {}, [], handler)
        async def scenario():
            task = asyncio.create_task(ToolExecutor(registry).execute(ToolCall("1", "slow")))
            try:
                async with asyncio.timeout(1):
                    while not started.is_set():
                        await asyncio.sleep(0.005)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertFalse(finished.is_set())
            finally:
                release.set()
                if not task.done():
                    task.cancel()
        asyncio.run(scenario())
        self.assertTrue(finished.is_set())
