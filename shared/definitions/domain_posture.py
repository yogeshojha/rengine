"""Sender, mail and zone checks read from a registrable domain's DNS."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.interest import TONE_INFO, TONE_WARNING

SPF_LOOKUP_LIMIT = 10
SPF_INCLUDE_DEPTH = 5
SPF_INCLUDE_CAP = 40
DKIM_MIN_BITS = 1024
MAX_EVIDENCE = 200
MAX_ZONES_PER_SCAN = 200
MAX_MAIL_HOSTS_PER_SCAN = 100
MX_BATCH_SIZE = 1000
MX_SWEEP_CAP = 5000
# names asked for MX first
MAIL_PREFIXES: tuple[str, ...] = (
    "mail",
    "smtp",
    "mx",
    "exchange",
    "webmail",
    "imap",
    "pop",
    "relay",
    "autodiscover",
    "mta",
    "post",
    "email",
)
MAX_ZONE_LENGTH = 253
POLICY_FETCH_TIMEOUT = 8
POLICY_MAX_BYTES = 64 * 1024
VALIDATING_RESOLVERS: tuple[str, ...] = ("1.1.1.1", "8.8.8.8", "9.9.9.9")
DEFAULT_DKIM_SELECTORS: tuple[str, ...] = (
    "default",
    "google",
    "selector1",
    "selector2",
    "k1",
    "k2",
    "s1",
    "s2",
    "dkim",
    "mail",
    "smtp",
    "mandrill",
    "mailjet",
    "sendgrid",
    "zendesk1",
    "amazonses",
    "pm",
    "protonmail",
    "mimecast20190108",
    "fm1",
)


class PostureCheck(StrEnum):
    SPF_MISSING = "spf_missing"
    SPF_ANY_SENDER = "spf_any_sender"
    SPF_SOFT_ALL = "spf_soft_all"
    SPF_MULTIPLE = "spf_multiple"
    SPF_LOOKUP_LIMIT = "spf_lookup_limit"
    DMARC_MISSING = "dmarc_missing"
    DMARC_NONE = "dmarc_none"
    DMARC_PARTIAL = "dmarc_partial"
    DMARC_SUBDOMAINS_OPEN = "dmarc_subdomains_open"
    DMARC_NO_REPORTING = "dmarc_no_reporting"
    DKIM_NONE_PROBED = "dkim_none_probed"
    DKIM_WEAK_KEY = "dkim_weak_key"
    MTA_STS_MISSING = "mta_sts_missing"
    MTA_STS_NOT_ENFORCED = "mta_sts_not_enforced"
    TLS_RPT_MISSING = "tls_rpt_missing"
    DNSSEC_MISSING = "dnssec_missing"
    DNSSEC_BROKEN = "dnssec_broken"
    CAA_MISSING = "caa_missing"


class PostureGroup(StrEnum):
    SENDER = "sender"
    MAIL = "mail"
    ZONE = "zone"


GROUP_LABELS: dict[str, str] = {
    PostureGroup.SENDER.value: "Sender authentication",
    PostureGroup.MAIL.value: "Mail transport",
    PostureGroup.ZONE.value: "Zone integrity",
}


class DnssecState(StrEnum):
    SIGNED = "signed"
    UNSIGNED = "unsigned"
    BROKEN = "broken"
    UNKNOWN = "unknown"


class MtaStsMode(StrEnum):
    ENFORCE = "enforce"
    TESTING = "testing"
    NONE = "none"
    UNREADABLE = "unreadable"


class SpfAll(StrEnum):
    FAIL = "fail"
    SOFTFAIL = "softfail"
    NEUTRAL = "neutral"
    PASS = "pass"  # noqa: S105
    ABSENT = "absent"


SPF_ALL_LABELS: dict[str, str] = {
    SpfAll.FAIL.value: "-all",
    SpfAll.SOFTFAIL.value: "~all",
    SpfAll.NEUTRAL.value: "?all",
    SpfAll.PASS.value: "+all",
    SpfAll.ABSENT.value: "no all",
}

# grammar-only values
ANY = "any"
NONE = "none"
TONES: tuple[str, ...] = (TONE_WARNING, TONE_INFO)

QUERY_FIELD = "posture"


@dataclass(frozen=True)
class CheckSpec:
    key: str
    label: str
    control: str
    help: str
    applies: str
    fix: str
    record: str
    group: str
    tone: str

    @property
    def query(self) -> str:
        return f"{QUERY_FIELD}:{self.key}"


CHECKS: tuple[CheckSpec, ...] = (
    CheckSpec(
        PostureCheck.SPF_MISSING.value,
        "No SPF record",
        "SPF",
        "No TXT record beginning v=spf1 on the zone.",
        "Every zone.",
        "Publish a v=spf1 record ending in -all.",
        "TXT",
        PostureGroup.SENDER.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.SPF_ANY_SENDER.value,
        "SPF allows any sender",
        "SPF all mechanism",
        "The SPF record ends in +all.",
        "Every zone with SPF.",
        "End the record with -all.",
        "TXT",
        PostureGroup.SENDER.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.SPF_MULTIPLE.value,
        "More than one SPF record",
        "SPF record count",
        "Two or more TXT records begin v=spf1. Receivers treat this as a permanent error.",
        "Every zone with SPF.",
        "Merge them into one record.",
        "TXT",
        PostureGroup.SENDER.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.SPF_LOOKUP_LIMIT.value,
        "SPF over the lookup limit",
        "SPF lookup count",
        "The record and its includes need more than 10 DNS lookups. Receivers treat this as a permanent error.",
        "Every zone with SPF.",
        "Flatten includes or remove unused mechanisms.",
        "TXT",
        PostureGroup.SENDER.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.DMARC_MISSING.value,
        "No DMARC record",
        "DMARC",
        "No TXT record beginning v=DMARC1 at _dmarc.",
        "Every zone.",
        "Publish v=DMARC1; p=reject; rua=mailto:<address> at _dmarc.",
        "_dmarc TXT",
        PostureGroup.SENDER.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.DMARC_NONE.value,
        "DMARC policy is none",
        "DMARC policy",
        "p=none. Failing mail is delivered and only reported.",
        "Every zone with DMARC.",
        "Raise p to quarantine, then reject.",
        "_dmarc TXT",
        PostureGroup.SENDER.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.DMARC_SUBDOMAINS_OPEN.value,
        "DMARC leaves subdomains open",
        "DMARC subdomain policy",
        "sp=none while p is quarantine or reject.",
        "Every zone with an enforcing DMARC policy.",
        "Remove sp or set it to reject.",
        "_dmarc TXT",
        PostureGroup.SENDER.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.DKIM_WEAK_KEY.value,
        "DKIM key under 1024 bits",
        "DKIM key size",
        "An RSA key below 1024 bits.",
        "Every zone with a readable RSA DKIM key.",
        "Rotate to a 2048-bit key.",
        "_domainkey TXT",
        PostureGroup.MAIL.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.DNSSEC_BROKEN.value,
        "DNSSEC validation fails",
        "DNSSEC",
        "A validating resolver answers SERVFAIL while a plain query answers.",
        "Every zone.",
        "Check the DS record and the zone's signatures.",
        "DS",
        PostureGroup.ZONE.value,
        TONE_WARNING,
    ),
    CheckSpec(
        PostureCheck.SPF_SOFT_ALL.value,
        "SPF does not fail unknown senders",
        "SPF all mechanism",
        "The SPF record ends in ~all or ?all, or has no all mechanism.",
        "Every zone with SPF.",
        "End the record with -all once every sender is listed.",
        "TXT",
        PostureGroup.SENDER.value,
        TONE_INFO,
    ),
    CheckSpec(
        PostureCheck.DMARC_PARTIAL.value,
        "DMARC applies to a share of mail",
        "DMARC pct",
        "pct is below 100.",
        "Every zone with an enforcing DMARC policy.",
        "Remove pct or set it to 100.",
        "_dmarc TXT",
        PostureGroup.SENDER.value,
        TONE_INFO,
    ),
    CheckSpec(
        PostureCheck.DMARC_NO_REPORTING.value,
        "DMARC without reporting",
        "DMARC rua",
        "The record names no rua address.",
        "Every zone with DMARC.",
        "Add rua=mailto:<address> to the record.",
        "_dmarc TXT",
        PostureGroup.SENDER.value,
        TONE_INFO,
    ),
    CheckSpec(
        PostureCheck.DKIM_NONE_PROBED.value,
        "No DKIM selector answered",
        "DKIM",
        "None of the probed selectors returned a key. Selectors outside the list are not checked.",
        "Every zone that publishes SPF.",
        "Publish the DKIM key the mail provider issued.",
        "_domainkey TXT",
        PostureGroup.MAIL.value,
        TONE_INFO,
    ),
    CheckSpec(
        PostureCheck.MTA_STS_MISSING.value,
        "No MTA-STS policy",
        "MTA-STS",
        "No TXT record at _mta-sts.",
        "Every zone that receives mail.",
        "Publish _mta-sts and serve the policy at mta-sts.<zone>.",
        "_mta-sts TXT",
        PostureGroup.MAIL.value,
        TONE_INFO,
    ),
    CheckSpec(
        PostureCheck.MTA_STS_NOT_ENFORCED.value,
        "MTA-STS not enforcing",
        "MTA-STS mode",
        "The policy mode is testing or none, or the policy file did not load.",
        "Every zone with an MTA-STS record.",
        "Set mode: enforce in the policy file.",
        "mta-sts.txt",
        PostureGroup.MAIL.value,
        TONE_INFO,
    ),
    CheckSpec(
        PostureCheck.TLS_RPT_MISSING.value,
        "No TLS reporting",
        "TLS-RPT",
        "No TXT record at _smtp._tls.",
        "Every zone that receives mail.",
        "Publish v=TLSRPTv1; rua=mailto:<address> at _smtp._tls.",
        "_smtp._tls TXT",
        PostureGroup.MAIL.value,
        TONE_INFO,
    ),
    CheckSpec(
        PostureCheck.DNSSEC_MISSING.value,
        "Zone not signed",
        "DNSSEC",
        "No DS record at the parent and no validated answer.",
        "Every zone.",
        "Sign the zone and publish the DS record at the registrar.",
        "DS",
        PostureGroup.ZONE.value,
        TONE_INFO,
    ),
    CheckSpec(
        PostureCheck.CAA_MISSING.value,
        "No CAA record",
        "CAA",
        "Any certificate authority may issue for the zone.",
        "Every zone.",
        "Publish CAA records naming the authorities in use.",
        "CAA",
        PostureGroup.ZONE.value,
        TONE_INFO,
    ),
)

CHECK_BY_KEY: dict[str, CheckSpec] = {c.key: c for c in CHECKS}
CHECK_KEYS: tuple[str, ...] = tuple(c.key for c in CHECKS)
CHECK_ORDER: dict[str, int] = {c.key: i for i, c in enumerate(CHECKS)}
WARNING_KEYS: tuple[str, ...] = tuple(c.key for c in CHECKS if c.tone == TONE_WARNING)
INFO_KEYS: tuple[str, ...] = tuple(c.key for c in CHECKS if c.tone == TONE_INFO)
KEYS_BY_TONE: dict[str, tuple[str, ...]] = {
    TONE_WARNING: WARNING_KEYS,
    TONE_INFO: INFO_KEYS,
}
QUERY_VALUES: tuple[str, ...] = (*CHECK_KEYS, *TONES, ANY, NONE)

# spoofable
SPOOFABLE_KEYS: tuple[str, ...] = (
    PostureCheck.SPF_MISSING.value,
    PostureCheck.SPF_ANY_SENDER.value,
    PostureCheck.SPF_LOOKUP_LIMIT.value,
    PostureCheck.SPF_MULTIPLE.value,
    PostureCheck.DMARC_MISSING.value,
    PostureCheck.DMARC_NONE.value,
    PostureCheck.DMARC_SUBDOMAINS_OPEN.value,
)
