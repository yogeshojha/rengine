import re

from sqlalchemy import case, func, literal

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


CORPORATE_SUFFIXES = (
    "incorporated",
    "corporation",
    "limited",
    "holdings",
    "company",
    "group",
    "gmbh",
    "corp",
    "llc",
    "ltd",
    "inc",
    "plc",
    "sas",
    "sarl",
    "bv",
    "nv",
    "ab",
    "as",
    "oy",
    "pty",
    "pte",
    "srl",
    "spa",
    "kk",
    "co",
    "sa",
)


def registrant_key(value: str | None) -> str:
    """A registrant name reduced to what two records must share to be the same party."""
    name = clean_name(value)
    if not name:
        return ""
    words = [w for w in re.split(r"[^a-z0-9]+", name.lower()) if w]
    while words and words[-1] in CORPORATE_SUFFIXES:
        words.pop()
    return "".join(words)


def redacted_name_sql(column):
    """The SQL half of is_redacted_name."""
    collapsed = func.btrim(func.regexp_replace(func.lower(column), r"\s+", " ", "g"))
    markers = "|".join(sorted(_REDACTED_NAME_MARKERS))
    return func.coalesce(collapsed, "").in_(
        sorted(_NON_IDENTIFYING_EXACT)
    ) | collapsed.op("~")(markers)


def registrant_key_sql(column):
    """The SQL half of registrant_key: the two must agree, or a match is invisible."""
    suffixes = "|".join(CORPORATE_SUFFIXES)
    key = func.regexp_replace(
        func.regexp_replace(
            func.lower(column),
            f"([^a-z0-9]+({suffixes}))+[^a-z0-9]*$",
            "",
            "g",
        ),
        "[^a-z0-9]",
        "",
        "g",
    )
    return case((redacted_name_sql(column), literal("")), else_=key)
