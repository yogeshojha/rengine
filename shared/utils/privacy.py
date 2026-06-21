import re

_WHITESPACE_RE = re.compile(r"\s+")

_NON_IDENTIFYING_EXACT = frozenset(
    {
        "",
        "-",
        "--",
        "n/a",
        "na",
        "none",
        "null",
        "nil",
        "no",
        "tbd",
        "unknown",
        "not applicable",
        "not available",
        "not disclosed",
    }
)

_REDACTED_NAME_MARKERS = frozenset(
    {
        "redacted",
        "redact",
        "privacy",
        "whoisguard",
        "data protected",
        "data protection",
        "non-public data",
        "withheld for",
        "domains by proxy",
        "by proxy",
        "proxy protection",
        "identity protection",
        "domain protection",
        "private registration",
        "registration private",
        "registrant private",
        "gdpr",
        "statutory masking",
        "masking enabled",
        "obscured whois",
        "privacydotlink",
        "anonymize",
        "anonymised",
        "anonymized",
    }
)

_REDACTED_EMAIL_MARKERS = frozenset(
    {
        "redacted",
        "privacy",
        "whoisguard",
        "proxy",
        "withheld",
        "gdpr",
        "anonym",
    }
)


def _normalize(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip().lower()


def is_redacted_name(value: str | None) -> bool:
    if not value:
        return True
    normalized = _normalize(value)
    if normalized in _NON_IDENTIFYING_EXACT:
        return True
    return any(marker in normalized for marker in _REDACTED_NAME_MARKERS)


def is_redacted_email(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    if "@" not in normalized:
        return True
    return any(marker in normalized for marker in _REDACTED_EMAIL_MARKERS)


def clean_name(value: str | None) -> str:
    if not value or is_redacted_name(value):
        return ""
    return value.strip()


def clean_email(value: str | None) -> str:
    if not value or is_redacted_email(value):
        return ""
    return value.strip().lower()
