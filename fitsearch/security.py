import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit


async def validate_public_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Le flux doit utiliser une adresse HTTP ou HTTPS valide")
    if parts.username or parts.password or (parts.port and parts.port not in {80, 443}):
        raise ValueError("Identifiants et ports personnalisés interdits")
    host = parts.hostname.lower().rstrip(".")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Les adresses locales ne sont pas autorisées")
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        if not literal_ip.is_global:
            raise ValueError("Le flux pointe vers une adresse privée ou locale")
        return url.strip()

    def resolve():
        return socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)

    try:
        addresses = await asyncio.to_thread(resolve)
    except socket.gaierror as exc:
        raise ValueError("Nom de domaine introuvable") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("Le flux pointe vers une adresse privée ou locale")
    return url.strip()
