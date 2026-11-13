"""Presupuesto de entrada completo en caracteres JSON, no una cuenta de tokens."""
import json
from dataclasses import asdict
from jarvis.domain.providers import ProviderError


def request_size(request):
    return len(json.dumps(asdict(request), ensure_ascii=False))


def enforce_budget(request, limit):
    if request_size(request) > limit:
        raise ProviderError("La solicitud completa supera el presupuesto de contexto; reduce la consulta o los resultados.")


def bounded_result(result, limit):
    text = json.dumps(result.as_dict(), ensure_ascii=False)
    if len(text) <= limit:
        return text
    # Mantener JSON válido y señalar que la vista previa NO es un resultado completo.
    payload = {"ok": result.ok, "truncated": True, "original_characters": len(text), "preview": ""}
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        payload["preview"] = text[:middle]
        if len(json.dumps(payload, ensure_ascii=False)) <= limit:
            low = middle
        else:
            high = middle - 1
    payload["preview"] = text[:low]
    return json.dumps(payload, ensure_ascii=False)
