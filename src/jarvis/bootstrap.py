"""Carga un perfil y construye el proveedor seleccionado."""

import json
from pathlib import Path

from jarvis.domain.providers import ModelProvider


def build_provider(path: Path, profile_name: str | None = None) -> tuple[ModelProvider, str]:
    """Devuelve el adaptador y el ID que se enviará en ModelRequest."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("profiles"), dict):
        raise ValueError("El archivo de modelos debe incluir un objeto profiles.")
    selected = profile_name if profile_name is not None else data.get("default_profile")
    if not isinstance(selected, str) or selected not in data["profiles"]:
        raise ValueError("El perfil seleccionado no existe en la configuración.")
    profile = data["profiles"][selected]
    if not isinstance(profile, dict) or profile.get("provider") != "bedrock":
        raise ValueError(f"El proveedor del perfil {selected!r} todavía no está integrado.")
    model = profile.get("model")
    region = profile.get("region")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"El perfil {selected!r} requiere un ID de modelo.")
    if not isinstance(region, str) or not region.strip():
        raise ValueError(f"El perfil {selected!r} requiere una región AWS.")

    import boto3
    from botocore.config import Config
    from jarvis.providers.bedrock.client import BedrockProvider

    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(connect_timeout=5, read_timeout=90, retries={"total_max_attempts": 1}),
    )
    return BedrockProvider(client), model
