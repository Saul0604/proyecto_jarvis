"""Busca nombres con un límite de exploración y sin seguir enlaces."""
import os
from pathlib import Path
from jarvis.permissions.files import FileAccess


def search_files(access: FileAccess, query: str, path: str = ".", limit: int = 20):
    directory = access.resolve(path)
    if not directory.is_dir():
        raise ValueError("La búsqueda requiere una carpeta.")
    results = []
    visited = 0
    errors = []
    for parent, directories, files in os.walk(directory, followlinks=False, onerror=errors.append):
        permitted = []
        for name in directories:
            candidate = Path(parent) / name
            try:
                access.resolve(str(candidate))
                if not candidate.is_symlink():
                    permitted.append(name)
            except (OSError, ValueError):
                continue
        directories[:] = permitted
        for name in directories + files:
            visited += 1
            if visited > 10000:
                return {"matches": results, "truncated": True, "skipped": len(errors)}
            if query.casefold() not in name.casefold():
                continue
            try:
                resolved = access.resolve(str(Path(parent) / name))
            except (OSError, ValueError):
                continue
            if len(results) == limit:
                return {"matches": results, "truncated": True, "skipped": len(errors)}
            results.append({"path": access.relative(resolved),
                            "type": "directory" if resolved.is_dir() else "file"})
    return {"matches": results, "truncated": False, "skipped": len(errors)}
