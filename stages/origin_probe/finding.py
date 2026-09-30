from __future__ import annotations

import hashlib

from shared.definitions.vulnerabilities import Protocol, Scanner, Severity
from shared.models.scan_correlation import OriginFinding
from shared.services.origin_exposure import DEFAULT_VHOST, ORIGIN_EXPOSED
from shared.utils.datetime import utc_now
from tools.nuclei.parser import Finding

_TEMPLATE = {
    ORIGIN_EXPOSED: "rengine-origin-exposed",
    DEFAULT_VHOST: "rengine-default-vhost",
}
_TITLE = {
    ORIGIN_EXPOSED: "Origin reachable outside the CDN",
    DEFAULT_VHOST: "Address serves a different site by default",
}
_SEVERITY = {"high": Severity.MEDIUM.value, "medium": Severity.LOW.value}
_FALLBACK = Severity.LOW.value
SEVERITIES: tuple[str, ...] = tuple({*_SEVERITY.values(), _FALLBACK})


def _evidence(found: OriginFinding) -> str:
    return ", ".join(item.label for item in found.evidence) or "none recorded"


def origin_finding(found: OriginFinding) -> Finding:
    """One origin-exposure correlation as a finding."""
    address = found.exposed.host or found.exposed.ip or ""
    kind = found.kind if found.kind in _TEMPLATE else ORIGIN_EXPOSED
    names = [sample.host for sample in found.fronted if sample.host]
    behind = (
        f"{names[0]}, which is behind a CDN" if names else "a hostname behind a CDN"
    )
    digest = hashlib.sha256(
        f"{Scanner.RENGINE.value}|{_TEMPLATE[kind]}|{address}|{behind}".encode()
    ).hexdigest()

    if kind == ORIGIN_EXPOSED:
        description = (
            f"{address} answers directly and serves the same application as {behind}. "
            f"Signals: {_evidence(found)}."
        )
        impact = (
            "Requests sent to the address bypass the CDN or WAF in front of the "
            "hostname."
        )
        remediation = (
            "Allow inbound traffic to the origin only from the CDN's address ranges, "
            "or move the origin to an unpublished address."
        )
    else:
        description = (
            f"Requests to {address} without a hostname return a different site "
            f"than {names[0] if names else 'the hostname'}. Signals: {_evidence(found)}."
        )
        impact = (
            "The default virtual host on this address exposes an application the "
            "hostname does not serve."
        )
        remediation = (
            "Configure the default virtual host on this address to return no content."
        )

    return Finding(
        fingerprint=digest,
        scanner=Scanner.RENGINE.value,
        template_id=_TEMPLATE[kind],
        template_name=_TITLE[kind],
        template_path=None,
        template_url=None,
        severity=_SEVERITY.get(found.confidence, _FALLBACK),
        protocol=Protocol.HTTP.value,
        matcher_name=found.confidence,
        extractor_name=None,
        extracted_results=[item.label for item in found.evidence],
        description=description,
        impact=impact,
        remediation=remediation,
        references=[],
        tags=["origin", "cdn"],
        authors=["rengine"],
        cve_ids=[],
        cwe_ids=[],
        cvss_metrics=None,
        cvss_score=None,
        epss_score=None,
        epss_percentile=None,
        cpe=None,
        is_kev=False,
        matched_at=address,
        host=found.exposed.host,
        ip=found.exposed.ip,
        port=found.exposed.port,
        scheme=None,
        url=found.exposed.url,
        path=None,
        request=None,
        response=None,
        curl_command=None,
        observed_at=utc_now(),
    )
