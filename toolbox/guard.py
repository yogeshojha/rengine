"""Destination guard for tools that send traffic."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from shared.utils.net import is_public_address, split_host_port
from toolbox.base import ToolError

DENIED_NETWORKS = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "224.0.0.0/4",
    "240.0.0.0/4",
    "::/128",
    "::1/128",
    "64:ff9b::/96",
    "64:ff9b:1::/48",
    "100::/64",
    "2001:db8::/32",
    "fc00::/7",
    "fe80::/10",
    "ff00::/8",
)


def hostname_of(value: str) -> str:
    raw = value.strip()
    if "://" in raw:
        return (urlsplit(raw).hostname or "").strip()
    return split_host_port(raw.split("/", 1)[0])[0].strip()


def require_public(value: str) -> list[str]:
    """Resolve the value and refuse any address that is not publicly routable."""
    host = hostname_of(value)
    if not host:
        msg = f"{value} is not a valid host."
        raise ToolError(msg)
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except OSError as exc:
        msg = f"{host} does not resolve: {exc.strerror or exc}."
        raise ToolError(msg) from exc
    for address in addresses:
        if not is_public_address(ipaddress.ip_address(address)):
            msg = (
                f"{host} resolves to {address}. "
                "Only publicly routable addresses can be probed."
            )
            raise ToolError(msg)
    return sorted(addresses)
