import ipaddress
import socket
from urllib.parse import urlsplit


def validate_public_https_url(raw: str, *, label: str = "URL") -> None:
    parts = urlsplit(raw)
    if parts.scheme != "https" or not parts.hostname:
        msg = f"{label} must be an https:// URL."
        raise ValueError(msg)
    try:
        infos = socket.getaddrinfo(parts.hostname, None)
    except OSError as exc:
        msg = f"Cannot resolve {label} host: {exc}"
        raise ValueError(msg) from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            msg = f"{label} resolves to a disallowed address."
            raise ValueError(msg)
