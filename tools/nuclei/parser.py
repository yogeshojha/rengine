"""Normalise one nuclei JSONL record into the shape reNgine stores."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from shared.definitions.vulnerabilities import (
    MAX_EVIDENCE_BYTES,
    Protocol,
    Scanner,
    coerce_protocol,
    coerce_severity,
    is_kev,
)

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_PROTOCOL_ALIASES = {
    "tcp": Protocol.NETWORK.value,
    "network": Protocol.NETWORK.value,
    "js": Protocol.JAVASCRIPT.value,
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [_CTRL.sub("", p).strip() for p in value.replace("\n", ",").split(",")]
        return [p for p in parts if p]
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_as_list(item))
        return out
    return [str(value)]


def _as_text(value: Any, limit: int = 0) -> str | None:
    if value is None:
        return None
    text = _CTRL.sub("", str(value)).strip()
    if not text:
        return None
    return text[:limit] if limit else text


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _timestamp(value: Any) -> datetime | None:
    text = _as_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class Finding:
    fingerprint: str
    scanner: str
    template_id: str
    template_name: str
    template_path: str | None
    template_url: str | None
    severity: str
    protocol: str
    matcher_name: str | None
    extractor_name: str | None
    extracted_results: list[str]
    description: str | None
    impact: str | None
    remediation: str | None
    references: list[str]
    tags: list[str]
    authors: list[str]
    cve_ids: list[str]
    cwe_ids: list[str]
    cvss_metrics: str | None
    cvss_score: float | None
    epss_score: float | None
    epss_percentile: float | None
    cpe: str | None
    is_kev: bool
    matched_at: str
    host: str | None
    ip: str | None
    port: int | None
    scheme: str | None
    url: str | None
    path: str | None
    request: str | None
    response: str | None
    curl_command: str | None
    interaction: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
    observed_at: datetime | None = None


def fingerprint(
    scanner: str, template_id: str, matcher: str | None, matched_at: str
) -> str:
    raw = f"{scanner}|{template_id}|{matcher or ''}|{matched_at}"
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()


def _hostname(candidate: str | None) -> str | None:
    if not candidate:
        return None
    value = candidate.strip()
    if "://" in value:
        parsed = urlsplit(value)
        return parsed.hostname or None
    head = value.split("/", 1)[0]
    if head.count(":") == 1:
        head = head.split(":", 1)[0]
    return head or None


def _port_of(record: dict, url: str | None) -> int | None:
    direct = _as_int(record.get("port"))
    if direct:
        return direct
    if url and "://" in url:
        parsed = urlsplit(url)
        if parsed.port:
            return parsed.port
        if parsed.scheme == "https":
            return 443
        if parsed.scheme == "http":
            return 80
    host = record.get("host") or ""
    if isinstance(host, str) and host.count(":") == 1:
        return _as_int(host.rsplit(":", 1)[1])
    return None


def parse_finding(record: dict, scanner: str = Scanner.NUCLEI.value) -> Finding | None:
    template_id = _as_text(record.get("template-id"), 200)
    if not template_id:
        return None
    info = record.get("info") if isinstance(record.get("info"), dict) else {}
    classification = info.get("classification")
    classification = classification if isinstance(classification, dict) else {}
    metadata = info.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}

    matched_at = (
        _as_text(record.get("matched-at"), 2000)
        or _as_text(record.get("url"), 2000)
        or _as_text(record.get("host"), 2000)
        or template_id
    )
    url = _as_text(record.get("url"), 2000) or (
        matched_at if "://" in matched_at else None
    )
    raw_type = (_as_text(record.get("type")) or "").lower()
    tags = _as_list(info.get("tags"))[:60]
    matcher = _as_text(record.get("matcher-name"), 200)

    return Finding(
        fingerprint=fingerprint(scanner, template_id, matcher, matched_at),
        scanner=scanner,
        template_id=template_id,
        template_name=_as_text(info.get("name"), 500) or template_id,
        template_path=_as_text(record.get("template"), 500)
        or _as_text(record.get("template-path"), 500),
        template_url=_as_text(record.get("template-url"), 1000),
        severity=coerce_severity(_as_text(info.get("severity"))),
        protocol=coerce_protocol(_PROTOCOL_ALIASES.get(raw_type, raw_type)),
        matcher_name=matcher,
        extractor_name=_as_text(record.get("extractor-name"), 200),
        extracted_results=_as_list(record.get("extracted-results"))[:50],
        description=_as_text(info.get("description")),
        impact=_as_text(info.get("impact")),
        remediation=_as_text(info.get("remediation")),
        references=_as_list(info.get("reference"))[:40],
        tags=tags,
        authors=_as_list(info.get("author"))[:20],
        cve_ids=[c.upper() for c in _as_list(classification.get("cve-id"))][:20],
        cwe_ids=[c.upper() for c in _as_list(classification.get("cwe-id"))][:20],
        cvss_metrics=_as_text(classification.get("cvss-metrics"), 200),
        cvss_score=_as_float(classification.get("cvss-score")),
        epss_score=_as_float(classification.get("epss-score")),
        epss_percentile=_as_float(classification.get("epss-percentile")),
        cpe=_as_text(classification.get("cpe"), 300),
        is_kev=is_kev(tags),
        matched_at=matched_at,
        host=_hostname(record.get("host")) or _hostname(matched_at),
        ip=_as_text(record.get("ip"), 45),
        port=_port_of(record, url),
        scheme=_as_text(record.get("scheme"), 16),
        url=url,
        path=_as_text(record.get("path"), 2000),
        request=_as_text(record.get("request"), MAX_EVIDENCE_BYTES),
        response=_as_text(record.get("response"), MAX_EVIDENCE_BYTES),
        curl_command=_as_text(record.get("curl-command"), MAX_EVIDENCE_BYTES),
        interaction=record.get("interaction") or {},
        extra={
            k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))
        },
        observed_at=_timestamp(record.get("timestamp")),
    )
