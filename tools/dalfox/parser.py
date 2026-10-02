from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from shared.definitions.ports import SCHEME_PORTS
from shared.definitions.vulnerabilities import (
    Protocol,
    Scanner,
    Severity,
    coerce_severity,
)
from shared.utils.net import url_port
from shared.utils.text import strip_control
from tools.nuclei.parser import Finding, fingerprint

_CLAIM_TYPES = frozenset({"V", "A", "R"})
_PROVEN_METHODS = frozenset({"oob"})


def _text(value: Any, limit: int = 0) -> str | None:
    if value is None:
        return None
    out = strip_control(str(value)).strip()
    if not out:
        return None
    return out[:limit] if limit else out


def _severity(value: Any) -> str:
    key = coerce_severity(str(value or ""))
    return Severity.LOW.value if key == Severity.UNKNOWN.value else key


def _template_id(record: dict) -> str:
    """Stable id per injection type and CWE."""
    parts = [
        str(record.get("inject_type") or record.get("detection_method") or ""),
        str(record.get("cwe") or "CWE-79"),
    ]
    return (
        "dalfox-xss-" + "-".join(p for p in parts if p).lower().replace(" ", "-")[:180]
    )


def parse_finding(record: dict) -> Finding | None:
    """A dalfox JSONL record, or None for the trailing meta line and non-claims."""
    if not isinstance(record, dict) or "findings_count" in record:
        return None
    result_type = str(record.get("type") or "").strip().upper()
    if result_type not in _CLAIM_TYPES:
        return None

    url = _text(record.get("data"), 2000)
    param = _text(record.get("param"), 200)
    matched_at = url or param or "dalfox"
    method = _text(record.get("detection_method")) or ""
    template_id = _template_id(record)
    matcher = param
    evidence_rung = "proven" if method in _PROVEN_METHODS else "observed"

    scheme = None
    host = None
    port = None
    if url and "://" in url:
        parsed = urlsplit(url)
        scheme = parsed.scheme
        host = parsed.hostname
        port = url_port(parsed) or SCHEME_PORTS.get((scheme or "").lower())

    name = (
        _text(record.get("type_description"), 500)
        or f"Cross-site scripting ({result_type})"
    )
    payload = _text(record.get("payload"), 2000)
    locator = (url.split("?", 1)[0] if url else "dalfox") + (
        f"#{param}" if param else ""
    )
    finding = Finding(
        fingerprint=fingerprint(Scanner.DALFOX.value, template_id, matcher, locator),
        scanner=Scanner.DALFOX.value,
        template_id=template_id,
        template_name=name,
        template_path=None,
        template_url=None,
        severity=_severity(record.get("severity")),
        protocol=Protocol.HTTP.value,
        matcher_name=_text(record.get("inject_type"), 200),
        extractor_name=None,
        extracted_results=[payload] if payload else [],
        description=_text(record.get("message_str")),
        impact=None,
        remediation=None,
        references=[],
        tags=["xss", "dast"],
        authors=["dalfox"],
        cve_ids=[],
        cwe_ids=[c for c in [_text(record.get("cwe"), 20)] if c],
        cvss_metrics=None,
        cvss_score=None,
        epss_score=None,
        epss_percentile=None,
        cpe=None,
        is_kev=False,
        matched_at=matched_at,
        host=host,
        ip=None,
        port=port,
        scheme=scheme,
        url=url,
        path=urlsplit(url).path if url and "://" in url else None,
        request=_text(record.get("request"), 100_000),
        response=_text(record.get("response"), 100_000),
        curl_command=None,
    )
    finding.extra = {
        "confidence": str(record.get("confidence") or ""),
        "detection_method": method,
    }
    if evidence_rung == "proven":
        finding.interaction = {"dalfox": method}
    return finding


__all__ = ["parse_finding"]
