import ipaddress
import re
import socket
from collections.abc import Iterable
from urllib.parse import SplitResult, urlsplit

_URL_QUERY = re.compile(r"(https?://[^\s'\"?#]+)\?[^\s'\"#]*", re.IGNORECASE)


def redact_url_queries(text: str) -> str:
    """Drop the query string of every URL in a message; queries carry API keys."""
    return _URL_QUERY.sub(r"\1?…", text)


def is_registry_routable(value: str) -> bool:
    """Whether an address or netblock sits in public space an RIR can hold a record for."""
    try:
        net = ipaddress.ip_network(value.strip(), strict=False)
    except ValueError:
        return False
    return net.is_global and not net.is_multicast


def is_public_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Whether an address may be reached from a server-side request."""
    return ip.is_global and not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_public_https_url(raw: str, *, label: str = "URL") -> None:
    parts = urlsplit(raw)
    if parts.scheme != "https" or not parts.hostname:
        msg = f"{label} must be an https:// URL."
        raise ValueError(msg)
    declared = unreadable_port(parts)
    if declared:
        msg = f"{label} carries {declared!r}, which is not a port number."
        raise ValueError(msg)
    try:
        infos = socket.getaddrinfo(parts.hostname, None)
    except OSError as exc:
        msg = f"Cannot resolve {label} host: {exc}"
        raise ValueError(msg) from exc
    for info in infos:
        if not is_public_address(ipaddress.ip_address(info[4][0])):
            msg = f"{label} resolves to a disallowed address."
            raise ValueError(msg)


def cert_covers(
    host: str | None, subject_cn: str | None, sans: Iterable[str] = ()
) -> bool:
    """Whether a certificate names the host presenting it."""
    if not host:
        return False
    target = host.strip().lower().rstrip(".")
    for raw in (subject_cn, *sans):
        if not raw:
            continue
        name = str(raw).strip().lower().rstrip(".")
        if name == target:
            return True
        if (
            name.startswith("*.")
            and target.endswith(name[1:])
            and target.count(".") == name.count(".")
        ):
            return True
    return False


def url_port(parts: SplitResult) -> int | None:
    """A URL's port, or None when absent or unreadable: reading .port is what raises."""
    try:
        return parts.port
    except ValueError:
        return None


def unreadable_port(parts: SplitResult) -> str | None:
    """The authority's port text when it is not a port number, else None."""
    _, declared = split_host_port(parts.netloc.rsplit("@", 1)[-1])
    return declared if declared and url_port(parts) is None else None


def bracketed(host: str) -> str:
    """An IPv6 literal in brackets. Anything else is returned as it is."""
    return f"[{host}]" if ":" in host and not host.startswith("[") else host


def host_port(host: str, port: int | str) -> str:
    """An authority a tool can parse."""
    return f"{bracketed(host)}:{port}"


def split_host_port(authority: str) -> tuple[str, str | None]:
    """The host and port of an authority, with an IPv6 literal unwrapped."""
    value = authority.strip()
    if value.startswith("["):
        literal, _, rest = value.partition("]")
        port = rest[1:] if rest.startswith(":") else ""
        return literal[1:], port or None
    if value.count(":") == 1:
        host, _, port = value.partition(":")
        return host, port or None
    return value, None
