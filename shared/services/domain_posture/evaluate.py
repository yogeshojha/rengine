"""Every check that applies to a zone, with its outcome."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from shared.definitions.domain_posture import (
    DKIM_MIN_BITS,
    MAX_EVIDENCE,
    SPF_LOOKUP_LIMIT,
    DnssecState,
    MtaStsMode,
    PostureCheck,
    SpfAll,
)
from shared.services.domain_posture import spf as spf_rules
from shared.services.domain_posture.records import ZoneRecords

C = PostureCheck

_DMARC_PREFIX = "v=dmarc1"
_TAG_RE = re.compile(r"\s*([a-z]+)\s*=\s*([^;]*)", re.IGNORECASE)
_ENFORCING = ("quarantine", "reject")
_MODE_RE = re.compile(r"^\s*mode\s*:\s*([a-z]+)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class Verdict:
    key: str
    failed: bool
    evidence: str | None = None


@dataclass
class Posture:
    verdicts: list[Verdict] = field(default_factory=list)
    spf: str | None = None
    spf_all: str | None = None
    spf_lookups: int | None = None
    dmarc: str | None = None
    dmarc_policy: str | None = None
    dmarc_subdomain_policy: str | None = None
    dmarc_pct: int | None = None
    dmarc_rua: bool | None = None
    dkim_selectors: list[str] = field(default_factory=list)
    dkim_key_bits: int | None = None
    mta_sts_mode: str | None = None

    @property
    def issues(self) -> list[str]:
        return [str(v.key) for v in self.verdicts if v.failed]

    @property
    def checked(self) -> list[str]:
        return [str(v.key) for v in self.verdicts]

    @property
    def evidence(self) -> dict[str, str]:
        return {
            str(v.key): v.evidence for v in self.verdicts if v.failed and v.evidence
        }


def _clip(value: str) -> str:
    value = " ".join(value.split())
    return value if len(value) <= MAX_EVIDENCE else value[: MAX_EVIDENCE - 1] + "…"


# ---------- parsing ----------


def dmarc_tags(record: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for chunk in record.split(";"):
        match = _TAG_RE.match(chunk)
        if match:
            out.setdefault(match.group(1).lower(), match.group(2).strip())
    return out


def is_dmarc(value: str) -> bool:
    return value.strip().lower().startswith(_DMARC_PREFIX)


def dkim_key_bits(record: str) -> int | None:
    """Modulus size of the RSA key a DKIM record publishes."""
    tags = dmarc_tags(record)
    if tags.get("k", "rsa").lower() != "rsa":
        return None
    raw = tags.get("p", "").replace(" ", "")
    if not raw:
        return None
    try:
        der = base64.b64decode(raw + "=" * (-len(raw) % 4), validate=False)
        key = serialization.load_der_public_key(der)
    except (ValueError, TypeError, UnsupportedAlgorithm):
        return None
    return key.key_size if isinstance(key, rsa.RSAPublicKey) else None


def mta_sts_mode(policy: str | None) -> str:
    if policy is None:
        return MtaStsMode.UNREADABLE.value
    match = _MODE_RE.search(policy)
    if not match:
        return MtaStsMode.UNREADABLE.value
    mode = match.group(1).lower()
    return (
        mode if mode in MtaStsMode.__members__.values() else MtaStsMode.UNREADABLE.value
    )


# ---------- checks ----------


def _sender(rec: ZoneRecords, out: Posture, add) -> None:
    records = spf_rules.spf_records(rec.txt)
    add(Verdict(C.SPF_MISSING, not records))
    if records:
        record = records[0]
        out.spf = record
        out.spf_all = spf_rules.all_qualifier(record)
        if out.spf_all == SpfAll.ABSENT.value and rec.spf_redirect_all:
            out.spf_all = rec.spf_redirect_all
        out.spf_lookups = rec.spf_lookups
        add(Verdict(C.SPF_MULTIPLE, len(records) > 1, _clip(f"{len(records)} records")))
        add(Verdict(C.SPF_ANY_SENDER, out.spf_all == SpfAll.PASS.value, _clip(record)))
        add(
            Verdict(
                C.SPF_SOFT_ALL,
                out.spf_all
                in (SpfAll.SOFTFAIL.value, SpfAll.NEUTRAL.value, SpfAll.ABSENT.value),
                _clip(record),
            )
        )
        if rec.spf_lookups is not None:
            over = rec.spf_lookups > SPF_LOOKUP_LIMIT
            shown = f"{rec.spf_lookups}{'+' if rec.spf_lookups_capped else ''} lookups"
            if over or not rec.spf_lookups_capped:
                add(Verdict(C.SPF_LOOKUP_LIMIT, over, shown))

    if rec.dmarc_unknown:
        return
    dmarc = [v for v in rec.dmarc if is_dmarc(v)]
    add(Verdict(C.DMARC_MISSING, not dmarc))
    if dmarc:
        record = dmarc[0]
        tags = dmarc_tags(record)
        policy = tags.get("p", "").lower() or None
        sub = tags.get("sp", "").lower() or None
        if rec.dmarc_inherited:
            policy = sub or policy
            sub = None
        out.dmarc = record
        out.dmarc_policy = policy
        out.dmarc_subdomain_policy = sub
        out.dmarc_rua = bool(tags.get("rua"))
        try:
            out.dmarc_pct = int(tags["pct"]) if "pct" in tags else None
        except ValueError:
            out.dmarc_pct = None
        shown = _clip(
            f"inherited from {rec.parent}: {record}" if rec.dmarc_inherited else record
        )
        add(Verdict(C.DMARC_NONE, policy not in _ENFORCING, shown))
        add(Verdict(C.DMARC_NO_REPORTING, not out.dmarc_rua, shown))
        if policy in _ENFORCING and not rec.dmarc_inherited:
            add(
                Verdict(
                    C.DMARC_SUBDOMAINS_OPEN,
                    sub == "none",
                    _clip(f"p={policy}; sp={sub}"),
                )
            )
        if policy in _ENFORCING:
            add(
                Verdict(
                    C.DMARC_PARTIAL,
                    out.dmarc_pct is not None and out.dmarc_pct < 100,  # noqa: PLR2004
                    f"pct={out.dmarc_pct}" if out.dmarc_pct is not None else None,
                )
            )


def _mail(rec: ZoneRecords, out: Posture, add) -> None:
    sends = bool(spf_rules.spf_records(rec.txt))
    if sends or rec.receives_mail:
        out.dkim_selectors = sorted(rec.dkim)
        add(Verdict(C.DKIM_NONE_PROBED, not rec.dkim))
        bits = [b for b in (dkim_key_bits(v) for v in rec.dkim.values()) if b]
        if bits:
            out.dkim_key_bits = min(bits)
            add(
                Verdict(
                    C.DKIM_WEAK_KEY,
                    out.dkim_key_bits < DKIM_MIN_BITS,
                    f"{out.dkim_key_bits}-bit key",
                )
            )
    if rec.receives_mail:
        add(Verdict(C.MTA_STS_MISSING, not rec.mta_sts))
        add(Verdict(C.TLS_RPT_MISSING, not rec.tls_rpt))
    if rec.mta_sts and rec.policy_fetched:
        out.mta_sts_mode = mta_sts_mode(rec.policy)
        add(
            Verdict(
                C.MTA_STS_NOT_ENFORCED,
                out.mta_sts_mode != MtaStsMode.ENFORCE.value,
                f"mode {out.mta_sts_mode}",
            )
        )


def _zone(rec: ZoneRecords, add) -> None:
    if rec.dnssec != DnssecState.UNKNOWN.value:
        add(Verdict(C.DNSSEC_BROKEN, rec.dnssec == DnssecState.BROKEN.value))
        add(Verdict(C.DNSSEC_MISSING, rec.dnssec == DnssecState.UNSIGNED.value))
    add(Verdict(C.CAA_MISSING, not rec.caa))


def evaluate(rec: ZoneRecords) -> Posture:
    """No verdict at all for a zone the resolver did not answer."""
    out = Posture()
    if not rec.answered:
        return out
    add = out.verdicts.append
    _sender(rec, out, add)
    _mail(rec, out, add)
    if rec.parent is None:
        _zone(rec, add)
    return out
