from __future__ import annotations

from datetime import datetime

from shared.utils.datetime import normalize_datetime


def _moment(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return normalize_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None


def parse_certificate(record: dict) -> dict | None:
    """One tlsx record reduced to the facts a stored certificate carries."""
    host = str(record.get("host") or "").strip().lower().rstrip(".")
    not_after = _moment(record.get("not_after"))
    if not host or not_after is None:
        return None
    issuer = record.get("issuer_org")
    fingerprints = record.get("fingerprint_hash")
    return {
        "host": host,
        "not_before": _moment(record.get("not_before")),
        "not_after": not_after,
        "expired": bool(record.get("expired")),
        "self_signed": bool(record.get("self_signed")),
        "issuer": (issuer[0] if isinstance(issuer, list) and issuer else None),
        "subject_cn": record.get("subject_cn") or None,
        "fingerprint": (
            fingerprints.get("sha256") if isinstance(fingerprints, dict) else None
        ),
    }
