"""Registra únicamente herramientas habilitadas por el usuario."""
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable

from jarvis.domain.tools import ToolDefinition
from jarvis.permissions.files import FileAccess
from jarvis.tools.files.list import list_files
from jarvis.tools.files.read import read_file
from jarvis.tools.files.search import search_files
from jarvis.tools.web.fetch import fetch_web_page
from jarvis.tools.web.search import search_web


@dataclass(frozen=True)
class RegisteredTool:
    definition: ToolDefinition
    handler: Callable


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def add(self, name, description, properties, required, handler):
        if name in self.tools:
            raise ValueError(f"Herramienta duplicada: {name}")
        schema = {"type": "object", "properties": properties,
                  "required": required, "additionalProperties": False}
        self.tools[name] = RegisteredTool(ToolDefinition(name, description, schema), handler)

    @property
    def definitions(self):
        return tuple(tool.definition for tool in self.tools.values())


def build_tools(root: Path | None = None, web: bool = False):
    registry = ToolRegistry()
    path = {"type": "string", "minLength": 1, "maxLength": 4096}
    query = {"type": "string", "minLength": 1, "maxLength": 500}
    limit = {"type": "integer", "minimum": 1, "maximum": 100}
    if root is not None:
        access = FileAccess(root)
        registry.add("list_files", "Lista una carpeta autorizada. Usa '.' para su raíz.",
                     {"path": path, "limit": limit}, [], partial(list_files, access))
        registry.add("search_files", "Busca nombres de archivos y carpetas, sin distinguir mayúsculas.",
                     {"query": query, "path": path, "limit": limit}, ["query"], partial(search_files, access))
        registry.add("read_file", "Lee texto UTF-8. offset y limit se expresan en caracteres.",
                     {"path": path, "offset": {"type": "integer", "minimum": 0, "maximum": 2000000},
                      "limit": {"type": "integer", "minimum": 1, "maximum": 12000}},
                     ["path"], partial(read_file, access))
    if web:
        registry.add("search_web", "Busca páginas públicas y devuelve URLs y fragmentos.",
                     {"query": query, "max_results": {"type": "integer", "minimum": 1, "maximum": 10}},
                     ["query"], search_web)
        registry.add("fetch_web_page", "Lee texto visible de una URL pública. No ejecuta JavaScript.",
                     {"url": path}, ["url"], fetch_web_page)
    return registry
