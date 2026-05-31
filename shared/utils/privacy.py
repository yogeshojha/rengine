"""Detection of privacy-protected / redacted WHOIS values.

RDAP and WHOIS responses routinely replace registrant identity with privacy
proxy placeholders such as ``REDACTED FOR PRIVACY``, ``Withheld for Privacy
ehf``, ``Domains By Proxy, LLC`` or ``Data Protected``. These placeholder
values are shared verbatim across thousands of unrelated domains, so using
them as correlation keys produces large clusters of false relationships.

This module is the single source of truth for recognizing such values. The
WHOIS parsing layer uses it to normalize redacted identities to an empty
string (so they are never written into a correlation column), and the
correlation layer uses it defensively so legacy rows that already contain a
placeholder are never grouped together.

The bias is deliberately toward *over*-detection: dropping a borderline value
from correlation is far cheaper than fabricating a relationship between
unrelated targets.
"""

import re

_WHITESPACE_RE = re.compile(r"\s+")

# Values that carry no identifying information. Matched exactly (after
# normalization) so a legitimate name merely *containing* one of these tokens
# is not discarded.
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

# Substrings that, when present in a registrant/organization name, indicate a
# privacy-proxy placeholder rather than a real identity. Curated so each entry
# adds coverage beyond the broad ``"privacy"`` marker.
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

# Substrings that mark an e-mail address as belonging to a privacy/proxy
# service rather than the real contact.
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
    """Lower-case, collapse internal whitespace and strip surrounding noise."""
    return _WHITESPACE_RE.sub(" ", value).strip().lower()


def is_redacted_name(value: str | None) -> bool:
    """Return ``True`` if a registrant/organization name is a privacy placeholder.

    Covers empty/non-identifying tokens (``"N/A"``, ``"Unknown"``) and the full
    family of privacy-proxy and GDPR-redaction strings.
    """
    if not value:
        return True
    normalized = _normalize(value)
    if normalized in _NON_IDENTIFYING_EXACT:
        return True
    return any(marker in normalized for marker in _REDACTED_NAME_MARKERS)


def is_redacted_email(value: str | None) -> bool:
    """Return ``True`` if an e-mail is missing or belongs to a privacy service.

    A value without an ``@`` is treated as redacted because it cannot be a
    real, correlatable address (RDAP often substitutes a sentence here).
    """
    if not value:
        return True
    normalized = value.strip().lower()
    if "@" not in normalized:
        return True
    return any(marker in normalized for marker in _REDACTED_EMAIL_MARKERS)


def clean_name(value: str | None) -> str:
    """Return the trimmed name, or ``""`` if it is a privacy placeholder.

    The original casing is preserved for non-redacted values so display and
    correlation use the registrant's actual name.
    """
    if not value or is_redacted_name(value):
        return ""
    return value.strip()


def clean_email(value: str | None) -> str:
    """Return the normalized e-mail, or ``""`` if redacted/unusable."""
    if not value or is_redacted_email(value):
        return ""
    return value.strip().lower()
