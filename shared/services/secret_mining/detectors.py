"""Compiled detectors and the checks that keep a match honest."""

from __future__ import annotations

import base64
import binascii
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from urllib.parse import urlsplit

from shared.definitions.secrets import (
    DETECTORS,
    EXAMPLE_DOMAINS,
    FILE_EXTENSIONS,
    MAX_SUBJECT_LENGTH,
    MAX_VALUE_LENGTH,
    MIN_ENTROPY_BITS,
    MIN_ENTROPY_LENGTH,
    PLACEHOLDER_LOCAL_PARTS,
    PLACEHOLDER_MARKS,
    PLACEHOLDER_PASSWORDS,
    TEMPLATE_MARKS,
    DetectorSpec,
    DropReason,
    SecretState,
    Validator,
)
from shared.utils.datetime import utc_now

_HEX_LOCAL = re.compile(r"^[0-9a-f]{20,}$")
_PEM_ALGORITHM = re.compile(r"-----BEGIN ((?:[A-Z]+ )?)PRIVATE KEY")
_PEM_END = "-----END"
_MAX_CLAIM = 200
_MIN_PLACEHOLDER_CHARS = 2
_MIN_PLACEHOLDER_LEN = 8


@dataclass(frozen=True)
class Match:
    kind: str
    value: str
    start: int
    end: int
    state: str
    subject: str | None
    meta: dict


@dataclass
class Sweep:
    matches: list[Match] = field(default_factory=list)
    dropped: Counter = field(default_factory=Counter)


@dataclass(frozen=True)
class Verdict:
    reason: str | None = None
    state: str = SecretState.EXPOSED.value
    subject: str | None = None
    meta: dict = field(default_factory=dict)
    value: str | None = None


@dataclass(frozen=True)
class Detector:
    spec: DetectorSpec
    regex: re.Pattern


@lru_cache(maxsize=1)
def detectors() -> tuple[Detector, ...]:
    return tuple(Detector(spec, re.compile(spec.pattern)) for spec in DETECTORS)


def detector_count() -> int:
    return len(DETECTORS)


def entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


def _placeholder(value: str) -> bool:
    lowered = value.lower()
    if any(mark in lowered for mark in PLACEHOLDER_MARKS):
        return True
    return (
        len(set(value)) <= _MIN_PLACEHOLDER_CHARS and len(value) >= _MIN_PLACEHOLDER_LEN
    )


def _subject(value: str | None) -> str | None:
    if not value:
        return None
    return value[:MAX_SUBJECT_LENGTH]


def _b64url(part: str) -> bytes:
    padded = part + "=" * (-len(part) % 4)
    return base64.urlsafe_b64decode(padded)


def _claim(payload: dict, name: str) -> str | None:
    value = payload.get(name)
    if value is None:
        return None
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value[:5])
    return str(value)[:_MAX_CLAIM]


def _validate_token(raw: str) -> Verdict:
    if _placeholder(raw):
        return Verdict(reason=DropReason.PLACEHOLDER.value)
    if len(raw) >= MIN_ENTROPY_LENGTH and entropy(raw) < MIN_ENTROPY_BITS:
        return Verdict(reason=DropReason.LOW_ENTROPY.value)
    return Verdict()


def _validate_public(raw: str) -> Verdict:
    if _placeholder(raw):
        return Verdict(reason=DropReason.PLACEHOLDER.value)
    subject = None
    if raw.startswith("https://"):
        subject = urlsplit(raw).hostname
    return Verdict(state=SecretState.PUBLIC.value, subject=_subject(subject))


def _validate_jwt(raw: str, now: datetime) -> Verdict:
    head, body, _signature = raw.split(".", 2)
    try:
        header = json.loads(_b64url(head))
        payload = json.loads(_b64url(body))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return Verdict(reason=DropReason.UNDECODABLE.value)
    if not isinstance(header, dict) or not isinstance(payload, dict):
        return Verdict(reason=DropReason.UNDECODABLE.value)
    if "alg" not in header:
        return Verdict(reason=DropReason.UNDECODABLE.value)
    expires = payload.get("exp")
    expired = False
    expires_at = None
    if isinstance(expires, (int, float)) and not isinstance(expires, bool):
        try:
            expires_at = datetime.fromtimestamp(expires, tz=UTC)
        except (OverflowError, OSError, ValueError):
            expires_at = None
        else:
            expired = expires_at < now
    meta = {
        "alg": _claim(header, "alg"),
        "typ": _claim(header, "typ"),
        "iss": _claim(payload, "iss"),
        "aud": _claim(payload, "aud"),
        "exp": expires_at.isoformat() if expires_at else None,
        "expired": expired,
    }
    state = SecretState.EXPIRED.value if expired else SecretState.EXPOSED.value
    return Verdict(state=state, subject=_subject(meta["iss"]), meta=meta)


def _validate_credential_url(raw: str) -> Verdict:
    lowered = raw.lower()
    if any(mark in lowered for mark in TEMPLATE_MARKS):
        return Verdict(reason=DropReason.TEMPLATE.value)
    try:
        parts = urlsplit(raw)
        username = parts.username
        password = parts.password
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return Verdict(reason=DropReason.UNDECODABLE.value)
    if not username or not password:
        return Verdict(reason=DropReason.PLACEHOLDER.value)
    if password.lower() in PLACEHOLDER_PASSWORDS or _placeholder(password):
        return Verdict(reason=DropReason.PLACEHOLDER.value)
    if host in EXAMPLE_DOMAINS or any(host.endswith(f".{d}") for d in EXAMPLE_DOMAINS):
        return Verdict(reason=DropReason.EXAMPLE_DOMAIN.value)
    meta = {
        "scheme": parts.scheme.lower(),
        "username": username[:_MAX_CLAIM],
        "host": host,
        "port": port,
    }
    return Verdict(subject=_subject(host), meta=meta)


def _validate_email(raw: str, text: str, end: int) -> Verdict:
    lowered = raw.lower()
    local, domain = lowered.rsplit("@", 1)
    tld = domain.rsplit(".", 1)[-1]
    if tld in FILE_EXTENSIONS:
        return Verdict(reason=DropReason.FILE_NAME.value)
    if domain in EXAMPLE_DOMAINS or any(
        domain.endswith(f".{d}") for d in EXAMPLE_DOMAINS
    ):
        return Verdict(reason=DropReason.EXAMPLE_DOMAIN.value)
    if local in PLACEHOLDER_LOCAL_PARTS or _placeholder(local):
        return Verdict(reason=DropReason.PLACEHOLDER.value)
    if _HEX_LOCAL.match(local):
        return Verdict(reason=DropReason.HEX_LOCAL_PART.value)
    if end < len(text) and text[end] == ":":
        return Verdict(reason=DropReason.PLACEHOLDER.value)
    return Verdict(
        state=SecretState.PUBLIC.value,
        subject=_subject(domain),
        meta={"domain": domain},
        value=lowered,
    )


def _validate_private_key(raw: str) -> Verdict:
    found = _PEM_ALGORITHM.search(raw)
    algorithm = (found.group(1).strip() if found else "") or "unspecified"
    complete = _PEM_END in raw
    return Verdict(meta={"algorithm": algorithm, "complete": complete})


def validate(  # noqa: PLR0911
    spec: DetectorSpec, raw: str, text: str, end: int, now: datetime
) -> Verdict:
    if len(raw) > MAX_VALUE_LENGTH:
        return Verdict(reason=DropReason.TOO_LONG.value)
    validator = spec.validator
    if validator == Validator.NONE.value:
        return _validate_public(raw)
    if validator == Validator.JWT.value:
        return _validate_jwt(raw, now)
    if validator == Validator.CREDENTIAL_URL.value:
        return _validate_credential_url(raw)
    if validator == Validator.EMAIL.value:
        return _validate_email(raw, text, end)
    if validator == Validator.PRIVATE_KEY.value:
        return _validate_private_key(raw)
    return _validate_token(raw)


def _resolve_overlaps(found: list[Match], dropped: Counter) -> list[Match]:
    """Keep the longest match at any position; a value inside another is not its own."""
    kept: list[Match] = []
    last_end = -1
    for match in sorted(found, key=lambda m: (m.start, -(m.end - m.start))):
        if match.start < last_end:
            dropped[DropReason.OVERLAP.value] += 1
            continue
        kept.append(match)
        last_end = match.end
    return kept


def find(text: str, *, now: datetime | None = None) -> Sweep:
    """Every honest match in one document."""
    now = now or utc_now()
    sweep = Sweep()
    if not text:
        return sweep
    found: list[Match] = []
    for detector in detectors():
        spec = detector.spec
        if not any(anchor in text for anchor in spec.anchors):
            continue
        for hit in detector.regex.finditer(text):
            raw = hit.group(1)
            start, end = hit.span(1)
            verdict = validate(spec, raw, text, end, now)
            if verdict.reason:
                sweep.dropped[verdict.reason] += 1
                continue
            found.append(
                Match(
                    kind=spec.key,
                    value=verdict.value or raw,
                    start=start,
                    end=end,
                    state=verdict.state,
                    subject=verdict.subject,
                    meta=verdict.meta,
                )
            )
    sweep.matches = _resolve_overlaps(found, sweep.dropped)
    return sweep
