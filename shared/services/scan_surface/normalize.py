"""One spelling per target: nuclei deduplicates its input byte for byte."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from shared.utils.net import bracketed, host_port

DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}


@dataclass(frozen=True)
class Root:
    scheme: str
    host: str
    port: int

    @property
    def value(self) -> str:
        return root_value(self.scheme, self.host, self.port)


def root_value(scheme: str, host: str, port: int | None) -> str:
    """`scheme://host[:port]`, lowercase, default port omitted, no path."""
    scheme = (scheme or "https").lower()
    host = (host or "").lower().strip("[]")
    literal = bracketed(host)
    if port and port != DEFAULT_PORTS.get(scheme):
        return f"{scheme}://{literal}:{port}"
    return f"{scheme}://{literal}"


def parse_root(
    url: str, *, scheme: str | None = None, port: int | None = None
) -> Root | None:
    """The origin a URL names, or None when it names none."""
    text = (url or "").strip()
    if not text:
        return None
    if "://" not in text:
        text = f"{scheme or 'https'}://{text}"
    parsed = urlsplit(text)
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    scheme_value = (parsed.scheme or scheme or "https").lower()
    try:
        port_value = parsed.port
    except ValueError:
        port_value = None
    port_value = port_value or port or DEFAULT_PORTS.get(scheme_value)
    if not port_value:
        return None
    return Root(scheme=scheme_value, host=host, port=int(port_value))


def service_value(host: str, port: int) -> str:
    """`host:port`, the form ssl and network checks take."""
    return host_port((host or "").lower(), int(port))


__all__ = ["DEFAULT_PORTS", "Root", "parse_root", "root_value", "service_value"]
