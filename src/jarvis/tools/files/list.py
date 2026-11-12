"""Lista una carpeta sin seguir enlaces hacia rutas externas."""
import os
from jarvis.permissions.files import FileAccess


def list_files(access: FileAccess, path: str = ".", limit: int = 50):
    directory = access.resolve(path)
    entries = []
    truncated = False
    skipped = 0
    with os.scandir(directory) as iterator:
        for entry in iterator:
            try:
                resolved = access.resolve(entry.path)
                if len(entries) == limit:
                    truncated = True
                    break
                entries.append({
                    "path": access.relative(resolved),
                    "type": "directory" if resolved.is_dir() else "file",
                })
            except (OSError, ValueError):
                skipped += 1
    return {"path": access.relative(directory), "entries": entries,
            "truncated": truncated, "skipped": skipped}
