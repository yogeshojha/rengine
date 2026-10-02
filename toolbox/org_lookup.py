"""Domains by organization: reading the input, matching names, merging evidence."""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from urllib.parse import urlsplit

from shared.definitions.domains import registrable_domain
from shared.utils.net import split_host_port
from shared.utils.privacy import CORPORATE_SUFFIXES, is_redacted_name

MAX_NAME_LENGTH = 200
MIN_KEY_LENGTH = 2
MAX_DOMAINS = 2000
MAX_NETWORKS = 24
MAX_SIMILAR = 8

_EXTRA_SUFFIXES = frozenset(
    {
        "ag",
        "se",
        "kg",
        "sl",
        "sau",
        "bhd",
        "sdn",
        "llp",
        "lp",
        "pvt",
        "private",
        "ltda",
        "sro",
        "kft",
        "zrt",
        "aps",
        "asa",
        "oyj",
        "gk",
        "the",
    }
)
_SUFFIXES = frozenset(CORPORATE_SUFFIXES) | _EXTRA_SUFFIXES
_INITIALISM = re.compile(r"\b([a-z])\.(?=[a-z]\b)")
_EMAIL = re.compile(r"^[^@\s]+@([^@\s]+\.[^@\s]+)$")
_ASN = re.compile(r"^as\d+$", re.IGNORECASE)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_WILDCARDS = ("%", "_")


class InputKind(StrEnum):
    ORGANIZATION = "organization"
    DOMAIN = "domain"
    EMAIL = "email"


class Evidence(StrEnum):
    CERTIFICATE = "certificate"
    REGISTRATION = "registration"


EVIDENCE_LABELS: dict[str, str] = {
    Evidence.CERTIFICATE.value: "Certificate",
    Evidence.REGISTRATION.value: "Registration",
}


class InputRefusedError(ValueError):
    """The input cannot be looked up; the message is shown as written."""


@dataclass(frozen=True)
class Query:
    kind: InputKind
    value: str


@dataclass
class DomainFacts:
    evidence: set[str] = field(default_factory=set)
    registered: date | None = None
    registrar: str = ""
    last_certificate: date | None = None


def fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def org_key(name: str | None) -> str:
    """An organization name reduced to what two spellings of it share."""
    if not name or is_redacted_name(name):
        return ""
    ascii_name = fold(name).lower()
    if not re.search(r"[a-z0-9]", ascii_name):
        return "".join(re.findall(r"\w+", name.casefold()))
    ascii_name = _INITIALISM.sub(r"\1", ascii_name)
    words = [w for w in re.split(r"[^a-z0-9]+", ascii_name) if w]
    if words and words[0] == "the":
        words = words[1:]
    while words and words[-1] in _SUFFIXES:
        words.pop()
    return "".join(words)


def lead_word(name: str) -> str:
    """The first distinctive word."""
    for word in re.split(r"[^A-Za-z0-9]+", fold(name)):
        if len(word) >= MIN_KEY_LENGTH + 1 and word.lower() not in _SUFFIXES:
            return word
    return ""


def _host_of(raw: str) -> str:
    candidate = raw.strip()
    if "://" in candidate:
        candidate = urlsplit(candidate).hostname or ""
    candidate = split_host_port(candidate.split("/", 1)[0])[0]
    return candidate.rstrip(".").lower().removeprefix("*.")


def _is_address(raw: str) -> bool:
    if _ASN.match(raw):
        return True
    try:
        ipaddress.ip_network(raw, strict=False)
    except ValueError:
        return False
    return True


def read(raw: str) -> Query:
    """Classify what was typed, refusing what cannot be looked up."""
    text = " ".join(raw.split())
    if not text:
        msg = "Enter an organization name, a domain or a registrant email."
        raise InputRefusedError(msg)
    if _CONTROL.search(raw):
        msg = "The input contains control characters."
        raise InputRefusedError(msg)
    if len(text) > MAX_NAME_LENGTH:
        msg = f"Enter at most {MAX_NAME_LENGTH} characters."
        raise InputRefusedError(msg)
    if _is_address(text):
        msg = f"{text} is an address or network. Use WHOIS for addresses and networks."
        raise InputRefusedError(msg)

    email = _EMAIL.match(text)
    if email:
        return Query(InputKind.EMAIL, text.lower())

    if " " not in text:
        host = _host_of(text)
        if "." in host and registrable_domain(host):
            return Query(InputKind.DOMAIN, registrable_domain(host))
        if "." in host and not registrable_domain(host):
            msg = f"{host} is a public suffix, not a domain."
            raise InputRefusedError(msg)

    if any(char in text for char in _WILDCARDS):
        msg = "Organization names cannot contain % or _."
        raise InputRefusedError(msg)
    if is_redacted_name(text):
        msg = f"{text} does not name an organization. Enter the organization behind the domain."
        raise InputRefusedError(msg)
    if len(org_key(text)) < MIN_KEY_LENGTH:
        msg = "Enter an organization name with at least two letters or digits."
        raise InputRefusedError(msg)
    return Query(InputKind.ORGANIZATION, text)


def subject_organization(dn: str | None) -> str:
    """The O= value of a certificate subject, or empty."""
    if not dn:
        return ""
    for part in re.split(r",\s*(?=[A-Za-z]+=)", dn):
        key, _, value = part.partition("=")
        if key.strip().upper() == "O":
            value = value.strip().replace("\\,", ",")
            return value if _is_organization(value) else ""
    return ""


def _is_organization(value: str) -> bool:
    if not value or is_redacted_name(value):
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return len(org_key(value)) >= MIN_KEY_LENGTH
    return False


def holder_name(description: str) -> str:
    """RIPEstat describes an AS as 'HANDLE - Holder name'."""
    _, sep, holder = description.partition(" - ")
    return holder.strip() if sep else description.strip()


def merge(
    certificates: dict[str, date | None],
    registrations: dict[str, tuple[date | None, str]],
) -> dict[str, DomainFacts]:
    merged: dict[str, DomainFacts] = {}
    for name, seen in certificates.items():
        facts = merged.setdefault(name, DomainFacts())
        facts.evidence.add(Evidence.CERTIFICATE.value)
        facts.last_certificate = seen
    for name, (registered, registrar) in registrations.items():
        facts = merged.setdefault(name, DomainFacts())
        facts.evidence.add(Evidence.REGISTRATION.value)
        facts.registered = registered
        facts.registrar = registrar
    return merged


def rank(name: str, facts: DomainFacts, targets: set[str], seen: set[str]) -> tuple:
    """New before seen before tracked; corroborated, then certified, first."""
    status = 2 if name in targets else 1 if name in seen else 0
    certified = Evidence.CERTIFICATE.value in facts.evidence
    return (status, -len(facts.evidence), not certified, name)
