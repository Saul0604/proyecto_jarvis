"""Extrae texto de páginas HTML y texto plano."""
from html.parser import HTMLParser
from jarvis.tools.web.http import get_public


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def fetch_web_page(url: str):
    final_url, content_type, body = get_public(url)
    mime = content_type.split(";")[0].strip().lower()
    if mime not in {"text/html", "text/plain", "application/xhtml+xml"}:
        raise ValueError("Solo se admite HTML y texto plano.")
    charset = "utf-8"
    for part in content_type.split(";")[1:]:
        if part.strip().lower().startswith("charset="):
            charset = part.split("=", 1)[1].strip().strip('"')
    text = body.decode(charset, errors="replace")
    if mime != "text/plain":
        parser = PageText()
        parser.feed(text)
        text = "\n".join(parser.parts)
    return {"url": final_url, "content": text[:12000], "truncated": len(text) > 12000}
