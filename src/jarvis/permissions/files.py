"""Resuelve rutas dentro de una carpeta autorizada por el usuario."""
from pathlib import Path


class FileAccess:
    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("La raíz autorizada debe ser una carpeta.")

    def resolve(self, path: str) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(self.root):
            raise PermissionError("La ruta está fuera de la carpeta autorizada.")
        return resolved

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()
