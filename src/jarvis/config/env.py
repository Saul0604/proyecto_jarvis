"""Carga asignaciones locales KEY=value."""
import os
import re
from pathlib import Path


def load_local_env(path: Path):
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except FileNotFoundError:
        return
    values = {}
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"Asignación inválida en .env, línea {number}.")
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"Comillas sin cerrar en .env, línea {number}.")
            value = value[1:-1]
        if value:
            values[key] = value
    for key, value in values.items():
        os.environ.setdefault(key, value)
