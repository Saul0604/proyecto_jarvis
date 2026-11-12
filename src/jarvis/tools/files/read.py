"""Lectura acotada de texto UTF-8, con desplazamiento por caracteres."""
from jarvis.permissions.files import FileAccess

EXTENSIONS = {".txt", ".md", ".csv", ".json"}
MAX_BYTES = 2_000_000


def read_file(access: FileAccess, path: str, offset: int = 0, limit: int = 8000):
    resolved = access.resolve(path)
    if not resolved.is_file() or resolved.suffix.lower() not in EXTENSIONS:
        raise ValueError("Usa un archivo .txt, .md, .csv o .json.")
    with resolved.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("El archivo supera el límite de 2 MB.")
    text = raw.decode("utf-8-sig")
    if "\x00" in text:
        raise ValueError("El archivo contiene datos binarios.")
    if offset > len(text):
        raise ValueError("El desplazamiento supera la longitud del archivo.")
    end = min(offset + limit, len(text))
    return {"path": access.relative(resolved), "content": text[offset:end],
            "offset": offset, "next_offset": end if end < len(text) else None,
            "total_characters": len(text), "truncated": end < len(text)}
