"""HTTP público acotado, con IP validada y fijada durante cada conexión."""
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin

MAX_BYTES = 1_000_000


def get_public(url: str, headers: dict | None = None):
    deadline = time.monotonic() + 20
    for _ in range(6):
        parts = urlsplit(url)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username is not None or parts.password is not None):
            raise ValueError("Se requiere una URL pública HTTP o HTTPS sin credenciales.")
        port = parts.port or (443 if parts.scheme == "https" else 80)
        if port not in {80, 443}:
            raise ValueError("Solo se permiten puertos web 80 y 443.")
        addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise PermissionError("La URL apunta a una red privada o reservada.")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("La descarga superó el tiempo permitido.")
        connection = http.client.HTTPConnection(parts.hostname, port, timeout=min(remaining, 10))
        try:
            # Conectar a la IP ya comprobada evita resolver otra dirección al abrir el socket.
            connection.sock = socket.create_connection((addresses[0][4][0], port), timeout=min(remaining, 10))
            if parts.scheme == "https":
                connection.sock = ssl.create_default_context().wrap_socket(
                    connection.sock, server_hostname=parts.hostname)
            target = parts.path or "/"
            if parts.query:
                target += "?" + parts.query
            request_headers = {"User-Agent": "Jarvis/0.1", "Accept-Encoding": "identity"}
            request_headers.update(headers or {})
            connection.request("GET", target, headers=request_headers)
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Redirección sin destino.")
                url = urljoin(url, location)
                headers = None  # No reenviar credenciales de búsqueda a otra URL.
                continue
            if response.status != 200:
                raise ValueError(f"El sitio respondió HTTP {response.status}.")
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError("El sitio devolvió una compresión no admitida.")
            chunks = []
            size = 0
            while size <= MAX_BYTES:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("La descarga superó el tiempo permitido.")
                if connection.sock:
                    connection.sock.settimeout(min(remaining, 10))
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("La página supera el límite de 1 MB.")
            return url, response.getheader("Content-Type", ""), b"".join(chunks)
        finally:
            connection.close()
    raise ValueError("Demasiadas redirecciones.")
