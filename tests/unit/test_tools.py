"""Pruebas locales de herramientas, permisos y ciclo del agente."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.domain.messages import Message, ModelResponse, Role, ToolCall
from jarvis.domain.providers import ProviderError
from jarvis.agent.runner import run_task
from jarvis.tools.registry import build_tools
from jarvis.tools.executor import ToolExecutor
from jarvis.tools.web.http import get_public
from jarvis.tools.web.fetch import fetch_web_page


class ToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "allowed"
        self.root.mkdir()
        (self.root / "presupuesto.txt").write_text("Total: 12000 MXN", encoding="utf-8")
        self.registry = build_tools(self.root)
        self.executor = ToolExecutor(self.registry)

    def call(self, name, **arguments):
        return asyncio.run(self.executor.execute(ToolCall("id", name, arguments)))

    def test_list_search_and_pagination(self):
        self.assertTrue(self.call("list_files").ok)
        result = self.call("search_files", query="PRESUPUESTO")
        self.assertEqual(result.data["matches"][0]["path"], "presupuesto.txt")
        part = self.call("read_file", path="presupuesto.txt", limit=7)
        rest = self.call("read_file", path="presupuesto.txt", offset=part.data["next_offset"])
        self.assertEqual(part.data["content"] + rest.data["content"], "Total: 12000 MXN")

    def test_permissions_and_validation(self):
        outside = self.root.parent / "secret.txt"
        outside.write_text("private")
        self.assertFalse(self.call("read_file", path="../secret.txt").ok)
        (self.root / "link.txt").symlink_to(outside)
        self.assertFalse(self.call("read_file", path="link.txt").ok)
        self.assertFalse(self.call("list_files", limit=True).ok)
        self.assertFalse(self.call("list_files", unexpected="x").ok)
        self.assertFalse(self.call("search_files", query=" ").ok)
        self.assertFalse(self.call("read_file", path="missing.txt").ok)
        self.assertFalse(self.call("delete_file", path="presupuesto.txt").ok)

    def test_size_and_unsupported_format(self):
        (self.root / "large.txt").write_bytes(b"x" * 2_000_001)
        (self.root / "program.exe").write_bytes(b"x")
        self.assertFalse(self.call("read_file", path="large.txt").ok)
        self.assertFalse(self.call("read_file", path="program.exe").ok)

    def test_web_private_addresses_blocked(self):
        for url in ("file:///etc/passwd", "http://127.0.0.1", "http://[::1]", "http://169.254.169.254"):
            with self.subTest(url=url), self.assertRaises((ValueError, PermissionError)):
                get_public(url)

    def test_web_extracts_text_and_origin(self):
        with patch("jarvis.tools.web.fetch.get_public", return_value=(
            "https://example.com", "text/html; charset=utf-8",
            b"<h1>Title</h1><script>hidden()</script><p>Hello</p>")):
            result = fetch_web_page("https://example.com")
        self.assertEqual(result["content"], "Title\nHello")
        self.assertFalse(result["truncated"])

    def test_search_api_response(self):
        with patch.dict("os.environ", {"BRAVE_SEARCH_API_KEY": "test"}), patch(
            "jarvis.tools.web.search.get_public", return_value=(
                "https://api.search.brave.com", "application/json",
                b'{"web":{"results":[{"title":"Example","url":"https://example.com","description":"Text"}]}}')
        ):
            executor = ToolExecutor(build_tools(web=True))
            result = asyncio.run(executor.execute(ToolCall("id", "search_web", {"query": "example"})))
        self.assertEqual(result.data["results"][0]["url"], "https://example.com")

    def test_agent_executes_tool_and_returns_result(self):
        class FakeProvider:
            def __init__(self):
                self.calls = 0

            async def generate(self, request):
                self.calls += 1
                if self.calls == 1:
                    return ModelResponse(Message(Role.ASSISTANT, tool_calls=(
                        ToolCall("read-1", "read_file", {"path": "presupuesto.txt"}),
                    )), request.model, "fake")
                result = json.loads(request.messages[-1].content)
                assert request.messages[-1].tool_call_id == "read-1"
                return ModelResponse(Message(Role.ASSISTANT, result["data"]["content"]),
                                     request.model, "fake")
        provider = FakeProvider()
        result = asyncio.run(run_task(provider, "test", "Lee el presupuesto", self.registry))
        self.assertEqual(result.message.content, "Total: 12000 MXN")
        self.assertEqual(provider.calls, 2)

    def test_agent_stops_repeated_tool_requests(self):
        class LoopProvider:
            async def generate(self, request):
                return ModelResponse(Message(Role.ASSISTANT, tool_calls=(
                    ToolCall("id", "list_files", {}),
                )), request.model, "fake")
        with self.assertRaises(ProviderError):
            asyncio.run(run_task(LoopProvider(), "test", "Lista", self.registry, max_steps=2))
