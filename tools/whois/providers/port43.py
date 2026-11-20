"""Port 43 WHOIS for a TLD whose registry runs no RDAP server."""

import ipaddress
import re
import socket
import ssl
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import idna

from shared.logging import get_logger
from shared.utils.net import is_public_address
from shared.utils.privacy import clean_name
from shared.utils.text import strip_control
from tools.banner.proxy import ProxyError, open_tunnel, resolve

logger = get_logger(__name__)

IANA_WHOIS = "whois.iana.org"
WHOIS_PORT = 43
CONNECT_SECONDS = 10
EXCHANGE_SECONDS = 15
MAX_RESPONSE_BYTES = 256 * 1024
REFERRAL_CACHE = 512
UNREACHABLE_SECONDS = 60
MAX_LINE_LENGTH = 1024

QUERY_FORMATS: dict[str, str] = {
    "whois.denic.de": "-T dn,ace {}",
    "whois.jprs.jp": "{}/e",
}

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S %z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%Y%m%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%a %b %d %Y",
    "%Y-%b-%d",
    "%d-%b-%Y",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y",
    "%d-%m-%Y",
    "%Y.%m.%d",
)

_REGISTERED_KEYS = (
    "creation date",
    "domain created",
    "domain name commencement date",
    "record created",
    "created",
    "registered",
    "registration date",
    "registration time",
    "registered on",
    "created on",
)
_CHANGED_KEYS = (
    "updated date",
    "last updated",
    "last updated on",
    "last update",
    "last modified",
    "modification date",
    "changed",
    "modified",
)
_EXPIRES_KEYS = (
    "registry expiry date",
    "registrar registration expiration date",
    "expiry date",
    "expiration date",
    "expiration time",
    "expire date",
    "expires on",
    "expires",
    "expire",
    "valid until",
    "paid-till",
)
_NS_KEYS = (
    "name server",
    "nameserver",
    "nameservers",
    "name servers",
    "nserver",
    "domain servers",
    "nameservers hostname",
    "name servers dns",
)
_NS_FALLBACK_KEYS = ("dns",)
_STATUS_KEYS = ("domain status", "flags", "status", "state")
_REGISTRAR_KEYS = (
    "registrar organization",
    "registrar organization name",
    "registrar name",
    "registrar",
    "sponsoring registrar",
    "registrar-name",
)
_REGISTRAR_URL_KEYS = (
    "registrar website",
    "registrar url",
    "registrar web",
    "registrar-url",
)
_REGISTRANT_NAME_KEYS = (
    "registrant organization",
    "registrant organisation",
    "registrant organization name",
    "registrant contact organisation",
    "registrant name",
    "registrant contact name",
    "holder name",
    "registrant",
    "org",
)
_NOT_REGISTERED = re.compile(
    r"no match|not found|no entries found|no data found|no object found"
    r"|not registered|status:\s*(available|free)\b",
    re.I,
)

_HOSTNAME = re.compile(
    r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+"
)
_LABEL = re.compile(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?")
_BRACKET = re.compile(r"\[([^\]]*)\]\s*(.*)")
_KEY = re.compile(r"[a-z][a-z0-9 ./_-]{0,40}")
_HEADER = re.compile(r"[A-Za-z][A-Za-z -]{1,39}")
_MAX_KEY_WORDS = 4
_NOTE = re.compile(r"\s*\(([^)]*)\)$")
_OFFSET = re.compile(r"(?:GMT|UTC)?\s*([+-])(\d{1,2}):?(\d{2})")
_ZONE_NAME = re.compile(r"\s+([A-Z]{2,5})$")
_NAMED_OFFSETS = {
    "UTC": timedelta(0),
    "GMT": timedelta(0),
    "JST": timedelta(hours=9),
    "CLT": timedelta(hours=-4),
    "CLST": timedelta(hours=-3),
}
_WITH_URL = re.compile(r"(.*?)\s*\(\s*(https?://\S+)\s*\)")
_STATUS_CUT = re.compile(r"\s+(?:https?://|\(|- )")
_HANDLE_KEY = "nic-hdl"
_REGISTRAR_HANDLE = re.compile(r"[A-Z0-9]+(-[A-Z0-9]+)+")
_SIGNING_KEYS = ("dnskey", "signing key")
_DOMAIN_KEYS = ("domain", "domain name", "domainname")
_BLOCKS = re.compile(r"\n[ \t]*\n")

_unreachable: dict[tuple[str, str | None], tuple[float, str]] = {}


class Port43Error(Exception):
    """Raised when a port-43 WHOIS lookup fails."""


def _left(deadline: float, cap: float = EXCHANGE_SECONDS) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeoutError
    return min(left, cap)


def _dial(server: str, deadline: float) -> socket.socket:
    try:
        infos = resolve(server, WHOIS_PORT, _left(deadline, CONNECT_SECONDS))
    except TimeoutError as e:
        msg = f"The resolver did not answer for {server}."
        raise _unreachable_error((server, None), msg) from e
    except (OSError, UnicodeError) as e:
        msg = f"{server} does not resolve."
        raise _unreachable_error((server, None), msg) from e
    refused: OSError | None = None
    for family, kind, proto, _, address in infos:
        try:
            public = is_public_address(ipaddress.ip_address(address[0]))
        except ValueError:
            public = False
        if not public:
            continue
        timeout = _left(deadline, CONNECT_SECONDS)
        sock = None
        try:
            sock = socket.socket(family, kind, proto)
            sock.settimeout(timeout)
            sock.connect(address)
        except OSError as e:
            if sock is not None:
                sock.close()
            refused = e
            continue
        return sock
    if refused is None:
        msg = f"{server} does not resolve to a public address."
        raise Port43Error(msg)
    raise refused


def _unreachable_error(key: tuple[str, str | None], msg: str) -> Port43Error:
    if len(_unreachable) >= REFERRAL_CACHE:
        _unreachable.clear()
    _unreachable[key] = (time.monotonic() + UNREACHABLE_SECONDS, msg)
    return Port43Error(msg)


def _connect(server: str, proxy_url: str | None, deadline: float) -> socket.socket:
    if not proxy_url:
        return _dial(server, deadline)
    timeout = _left(deadline, CONNECT_SECONDS)
    try:
        return open_tunnel(
            proxy_url, server, WHOIS_PORT, timeout, verify=True, deadline=deadline
        )
    except ssl.SSLCertVerificationError as e:
        msg = "The proxy certificate did not verify."
        raise _unreachable_error((server, proxy_url), msg) from e
    except (ProxyError, OSError, ValueError) as e:
        msg = f"The proxy did not open a connection to {server} on port 43."
        raise _unreachable_error((server, proxy_url), msg) from e


def _query(server: str, query: str, proxy_url: str | None = None) -> str:
    key = (server, proxy_url)
    until, known = _unreachable.get(key, (0.0, ""))
    if until > time.monotonic():
        raise Port43Error(known)
    deadline = time.monotonic() + EXCHANGE_SECONDS
    chunks: list[bytes] = []
    size = 0
    try:
        with _connect(server, proxy_url, deadline) as conn:
            conn.settimeout(_left(deadline))
            conn.sendall(f"{query}\r\n".encode())
            while size < MAX_RESPONSE_BYTES:
                conn.settimeout(_left(deadline))
                chunk = conn.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
    except OSError as e:
        logger.debug("port-43 WHOIS to %s failed: %s", server, type(e).__name__)
        msg = f"{server} did not answer on port 43."
        raise _unreachable_error(key, msg) from e
    return strip_control(b"".join(chunks).decode("utf-8", errors="replace"))


@lru_cache(maxsize=REFERRAL_CACHE)
def whois_server_for(tld: str, proxy_url: str | None = None) -> str:
    """The registry's WHOIS server, as the IANA root lists it."""
    if not _LABEL.fullmatch(tld):
        msg = f".{tld} is not a top-level domain."
        raise Port43Error(msg)
    for line in _query(IANA_WHOIS, tld, proxy_url).splitlines():
        key, _, value = line.partition(":")
        server = value.strip().lower().rstrip(".")
        if key.strip().lower() in ("whois", "refer") and _HOSTNAME.fullmatch(server):
            return server
    msg = f"IANA lists no WHOIS server for .{tld}."
    raise Port43Error(msg)


def _offset(note: str) -> timedelta | None:
    note = note.strip()
    if note in _NAMED_OFFSETS:
        return _NAMED_OFFSETS[note]
    match = _OFFSET.fullmatch(note)
    if not match:
        return None
    sign = -1 if match[1] == "-" else 1
    return sign * timedelta(hours=int(match[2]), minutes=int(match[3]))


def _parse_date(value: str) -> datetime | None:
    value = value.strip().rstrip(".")
    offset = timedelta(0)
    note = _NOTE.search(value) or _ZONE_NAME.search(value)
    if note:
        offset = _offset(note[1])
        value = value[: note.start()].strip()
    if offset is None:
        return None
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)  # noqa: DTZ007
        except ValueError:
            continue
        if parsed.tzinfo:
            return parsed
        return parsed.replace(tzinfo=timezone(offset))
    return None


def _comment(stripped: str) -> bool:
    if stripped.startswith(("%", "#", ">>>", "---")):
        return True
    return stripped.startswith("*") and stripped.endswith("*")


def _split(stripped: str) -> tuple[str, bool, str]:
    """Key, whether the line carries a separator, and value."""
    stripped = stripped.removeprefix("** ")
    bracket = _BRACKET.fullmatch(stripped)
    if bracket:
        return " ".join(bracket[1].lower().split()), True, bracket[2].strip()
    key, sep, value = stripped.partition(":")
    key = key.rstrip()
    if key.endswith(".."):
        key = key.rstrip(".")
    return " ".join(key.lower().split()), bool(sep), value.strip()


def _label(key: str) -> bool:
    return bool(_KEY.fullmatch(key)) and len(key.split()) <= _MAX_KEY_WORDS


def _header(stripped: str) -> bool:
    return bool(_HEADER.fullmatch(stripped)) and len(stripped.split()) <= _MAX_KEY_WORDS


def _names_host(stripped: str) -> bool:
    first = stripped.split(maxsplit=1)[0].lower().rstrip(".")
    return bool(_HOSTNAME.fullmatch(first))


def parse_fields(text: str) -> dict[str, list[str]]:
    """Key to values, from flat lines and from lines under a section header."""
    fields: dict[str, list[str]] = {}
    section = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            section = ""
            continue
        if len(raw) > MAX_LINE_LENGTH or _comment(stripped):
            continue
        indented = raw[:1] in (" ", "\t")
        key, sep, value = _split(stripped)
        if section and _names_host(stripped):
            fields.setdefault(section, []).append(stripped)
            continue
        if indented and section:
            if sep and value and _label(key):
                fields.setdefault(f"{section} {key}", []).append(value)
            else:
                fields.setdefault(section, []).append(stripped)
            continue
        if sep and not value:
            section = key
            continue
        if not sep:
            if section:
                fields.setdefault(section, []).append(stripped)
            elif _header(stripped):
                section = stripped.lower()
            continue
        fields.setdefault(key, []).append(value)
        if section:
            fields.setdefault(f"{section} {key}", []).append(value)
    return fields


def _first(fields: dict[str, list[str]], keys: tuple[str, ...]) -> str:
    for key in keys:
        for value in fields.get(key, []):
            if value:
                return value
    return ""


def _tokens(fields: dict[str, list[str]], keys: tuple[str, ...]) -> list[str]:
    """First token of every value."""
    out: list[str] = []
    for key in keys:
        for value in fields.get(key, []):
            token = value.split()[0] if value else ""
            if token and token not in out:
                out.append(token)
    return out


def _nameservers(fields: dict[str, list[str]], domain: str) -> list[str]:
    hosts = [ns.lower().rstrip(".") for ns in _tokens(fields, _NS_KEYS)]
    if hosts:
        return hosts
    fallback = [ns.lower().rstrip(".") for ns in _tokens(fields, _NS_FALLBACK_KEYS)]
    return [ns for ns in fallback if ns != domain.lower()]


def _statuses(fields: dict[str, list[str]]) -> list[str]:
    for key in _STATUS_KEYS:
        values = fields.get(key)
        if not values:
            continue
        out: list[str] = []
        for value in values:
            for part in value.split(","):
                status = _STATUS_CUT.split(part.strip(), maxsplit=1)[0].strip()
                if status and status not in out:
                    out.append(status)
        return out
    return []


def _holder(text: str, handle: str, key: str = _HANDLE_KEY) -> str:
    """The organization or person a registry handle names."""
    for block in _BLOCKS.split(text):
        fields = parse_fields(block)
        if handle.lower() in (v.lower() for v in fields.get(key, [])):
            return _first(fields, ("organization", "personname", "name"))
    return ""


def _registrant(fields: dict[str, list[str]], text: str) -> str:
    name = _first(fields, _REGISTRANT_NAME_KEYS)
    if name and _HANDLE_KEY in fields:
        name = _holder(text, name) or name
    return clean_name(name)


def _signed(fields: dict[str, list[str]]) -> bool:
    if _first(fields, ("dnssec",)).lower().startswith("signed"):
        return True
    if _first(fields, ("signed", "dnssec signed")).lower() == "yes":
        return True
    if _first(fields, _SIGNING_KEYS):
        return True
    return any(key == "keys" or key.startswith("keys ") for key in fields)


def _domain_block(text: str) -> dict[str, list[str]]:
    """The fields of the block that names the domain."""
    for block in _BLOCKS.split(text):
        fields = parse_fields(block)
        if any(key in fields for key in _DOMAIN_KEYS):
            return fields
    return {}


def to_whoisit_shape(domain: str, server: str, text: str) -> dict[str, Any]:
    text = text.replace("\r\n", "\n")
    fields = parse_fields(text)
    own = _domain_block(text)

    def date(keys: tuple[str, ...]) -> datetime | None:
        return _parse_date(_first(own, keys) or _first(fields, keys))

    nameservers = _nameservers(fields, domain)
    registrar = _first(fields, _REGISTRAR_KEYS)
    registrar_url = _first(fields, _REGISTRAR_URL_KEYS)
    with_url = _WITH_URL.fullmatch(registrar)
    if with_url:
        registrar, registrar_url = with_url[1], registrar_url or with_url[2]
    if _REGISTRAR_HANDLE.fullmatch(registrar):
        registrar = _holder(text, registrar, "registrar") or registrar
    registrant = _registrant(fields, text)
    entities: dict[str, list[dict[str, Any]]] = {}
    if registrar:
        entities["registrar"] = [{"name": registrar, "url": registrar_url}]
    if registrant:
        entities["registrant"] = [
            {"name": registrant, "email": _first(fields, ("registrant email",))}
        ]
    abuse = _first(fields, ("registrar abuse contact email",))
    if abuse:
        entities["abuse"] = [{"email": abuse}]
    return {
        "type": "domain",
        "name": _first(fields, ("domain name", "domain")).lower() or domain,
        "handle": _first(fields, ("registry domain id",)),
        "whois_server": server,
        "registration_date": date(_REGISTERED_KEYS),
        "last_changed_date": date(_CHANGED_KEYS),
        "expiration_date": date(_EXPIRES_KEYS),
        "nameservers": nameservers,
        "status": _statuses(fields),
        "dnssec": _signed(fields),
        "entities": entities,
        "description": ["WHOIS port 43 record"],
    }


def _evidence(shape: dict[str, Any]) -> bool:
    return bool(
        shape["entities"]
        or shape["nameservers"]
        or shape["registration_date"]
        or shape["last_changed_date"]
        or shape["expiration_date"]
    )


def _ascii(domain: str) -> str:
    try:
        encoded = idna.encode(domain, uts46=True).decode("ascii")
    except (idna.IDNAError, UnicodeError):
        encoded = ""
    if not _HOSTNAME.fullmatch(encoded):
        msg = f"{domain} is not a domain name."
        raise Port43Error(msg)
    return encoded


def lookup_domain(domain: str, proxy_url: str | None = None) -> dict[str, Any]:
    domain = _ascii(domain)
    server = whois_server_for(domain.rsplit(".", 1)[-1], proxy_url)
    query = QUERY_FORMATS.get(server, "{}").format(domain)
    text = _query(server, query, proxy_url)
    shape = to_whoisit_shape(domain, server, text)
    if not _evidence(shape):
        if _NOT_REGISTERED.search(text):
            msg = f"{domain} is not registered."
            raise Port43Error(msg)
        if not shape["status"]:
            msg = f"{server} returned no registration data for {domain}."
            raise Port43Error(msg)
    logger.debug("port-43 WHOIS for %s answered by %s", domain, server)
    return shape
