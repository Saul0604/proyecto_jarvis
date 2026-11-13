"""Busca títulos, URLs y fragmentos mediante Brave Search API."""
from jarvis.tools.errors import ToolConfigurationError
import json
import os
from urllib.parse import urlencode
from jarvis.tools.web.http import get_public


def search_web(query: str, max_results: int = 5):
    key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        raise ToolConfigurationError("Configura BRAVE_SEARCH_API_KEY para usar búsqueda web.")
    url = "https://api.search.brave.com/res/v1/web/search?" + urlencode(
        {"q": query, "count": max_results})
    _, _, body = get_public(url, {"X-Subscription-Token": key, "Accept": "application/json"})
    data = json.loads(body)
    results = data.get("web", {}).get("results", [])
    return {"query": query, "results": [
        {"title": item.get("title", "")[:500], "url": item["url"],
         "snippet": item.get("description", "")[:1500]}
        for item in results[:max_results]
    ]}
