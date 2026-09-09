"""Destination guard for tools that send traffic."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from toolbox.base import ToolError


def hostname_of(value: str) -> str:
    raw = value.strip()
    if "://" in raw:
        return (urlsplit(raw).hostname or "").strip()
    return (
        raw.split("/", 1)[0].rsplit(":", 1)[0].strip() if raw.count(":") <= 1 else raw
    )


def _blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def require_public(value: str) -> list[str]:
    """Resolve the value and refuse any address that is not publicly routable."""
    host = hostname_of(value)
    if not host:
        msg = f"{value} is not a valid host."
        raise ToolError(msg)
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except OSError as exc:
        msg = f"{host} does not resolve ({exc.strerror or exc})."
        raise ToolError(msg) from exc
    for address in addresses:
        if _blocked(ipaddress.ip_address(address)):
            msg = (
                f"{host} resolves to {address}. "
                "Only publicly routable addresses can be probed."
            )
            raise ToolError(msg)
    return sorted(addresses)
