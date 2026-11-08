"""Legacy port-43 WHOIS, for a TLD whose registry runs no RDAP server (.be, ...).

Returns the same dict shape whoisit does, so parse_domain_response reads it.
"""

import re
import socket
from datetime import UTC, datetime
from typing import Any

from shared.logging import get_logger

logger = get_logger(__name__)

IANA_WHOIS = "whois.iana.org"
WHOIS_PORT = 43
TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 256 * 1024

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%a %b %d %Y",  # .be: Wed Mar 20 1996
    "%d-%b-%Y",
    "%d.%m.%Y",
    "%Y.%m.%d",
)

_REGISTERED_KEYS = ("creation date", "created", "registered", "registration date")
_CHANGED_KEYS = ("updated date", "last updated", "last modified", "changed", "modified")
_EXPIRES_KEYS = (
    "registry expiry date",
    "registrar registration expiration date",
    "expiry date",
    "expiration date",
    "expires",
    "paid-till",
)
_NS_KEYS = ("name server", "nameserver", "nameservers", "nserver")
# first key that has values wins: .be puts EPP flags under Flags and
# availability under Status
_STATUS_KEYS = ("domain status", "flags", "state", "status")
_REGISTRANT_NAME_KEYS = ("registrant organization", "registrant name", "registrant")
_NOT_REGISTERED = re.compile(
    r"no match|not found|no entries found|status:\s*available", re.I
)


class Port43Error(Exception):
    """Raised when a port-43 WHOIS lookup fails."""


def _query(server: str, query: str) -> str:
    try:
        with socket.create_connection(
            (server, WHOIS_PORT), timeout=TIMEOUT_SECONDS
        ) as conn:
            conn.sendall(f"{query}\r\n".encode())
            chunks: list[bytes] = []
            size = 0
            while chunk := conn.recv(4096):
                chunks.append(chunk)
                size += len(chunk)
                if size >= MAX_RESPONSE_BYTES:
                    break
    except OSError as e:
        msg = f"WHOIS query to {server} failed: {e}"
        raise Port43Error(msg) from e
    return b"".join(chunks).decode("utf-8", errors="replace")


def whois_server_for(tld: str) -> str:
    """The registry's WHOIS server, as the IANA root lists it."""
    for line in _query(IANA_WHOIS, tld).splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower() in ("whois", "refer") and value.strip():
            return value.strip().lower()
    msg = f"IANA lists no WHOIS server for .{tld}"
    raise Port43Error(msg)


def _parse_date(value: str) -> datetime | None:
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)  # noqa: DTZ007
        except ValueError:
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def parse_fields(text: str) -> dict[str, list[str]]:
    """Key -> values, from flat `Key: value` lines and from indented sections.

    A section is a `Header:` line with no value, followed by indented lines
    (the .be layout); its lines are kept under the header, and an indented
    `Name: value` inside it also lands under `header name`.
    """
    fields: dict[str, list[str]] = {}
    section = ""
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith(("%", "#", ">>>")):
            if not raw.strip():
                section = ""
            continue
        indented = raw[:1] in (" ", "\t")
        key, sep, value = raw.strip().partition(":")
        key = key.strip().lower()
        value = value.strip()
        if indented and section:
            if sep and value and " " not in key:
                fields.setdefault(f"{section} {key}", []).append(value)
            else:
                fields.setdefault(section, []).append(raw.strip())
            continue
        if sep and not value:
            section = key
            continue
        section = ""
        if sep:
            fields.setdefault(key, []).append(value)
    return fields


def _first(fields: dict[str, list[str]], keys: tuple[str, ...]) -> str:
    for key in keys:
        for value in fields.get(key, []):
            if value:
                return value
    return ""


def _tokens(fields: dict[str, list[str]], keys: tuple[str, ...]) -> list[str]:
    """First token of every value (drops an EPP status URL or a glue address)."""
    out: list[str] = []
    for key in keys:
        for value in fields.get(key, []):
            token = value.split()[0] if value else ""
            if token and token not in out:
                out.append(token)
    return out


def _statuses(fields: dict[str, list[str]]) -> list[str]:
    for key in _STATUS_KEYS:
        if fields.get(key):
            return _tokens(fields, (key,))
    return []


def to_whoisit_shape(domain: str, server: str, text: str) -> dict[str, Any]:
    fields = parse_fields(text)
    nameservers = [ns.lower().rstrip(".") for ns in _tokens(fields, _NS_KEYS)]
    registrar = _first(fields, ("registrar name", "registrar", "sponsoring registrar"))
    registrant = _first(fields, _REGISTRANT_NAME_KEYS)
    if registrant.lower().startswith("not shown"):
        registrant = ""
    dnssec_value = _first(fields, ("dnssec",)).lower()
    dnssec = dnssec_value.startswith("signed") or any(
        key == "keys" or key.startswith("keys ") for key in fields
    )
    entities: dict[str, list[dict[str, Any]]] = {}
    if registrar:
        entities["registrar"] = [
            {
                "name": registrar,
                "url": _first(fields, ("registrar website", "registrar url")),
            }
        ]
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
        "registration_date": _parse_date(_first(fields, _REGISTERED_KEYS)),
        "last_changed_date": _parse_date(_first(fields, _CHANGED_KEYS)),
        "expiration_date": _parse_date(_first(fields, _EXPIRES_KEYS)),
        "nameservers": nameservers,
        "status": _statuses(fields),
        "dnssec": dnssec,
        "entities": entities,
        "description": ["Legacy port-43 WHOIS: the registry runs no RDAP server"],
    }


def lookup_domain(domain: str) -> dict[str, Any]:
    tld = domain.rsplit(".", 1)[-1]
    server = whois_server_for(tld)
    text = _query(server, domain)
    if _NOT_REGISTERED.search(text) and not parse_fields(text).get("registrar"):
        msg = f"{server} holds no registration for {domain}"
        raise Port43Error(msg)
    logger.debug("port-43 WHOIS for %s answered by %s", domain, server)
    return to_whoisit_shape(domain, server, text)
