from __future__ import annotations

import hashlib

from shared.definitions.vulnerabilities import Protocol, Scanner, Severity
from shared.models.scan_correlation import OriginFinding
from shared.utils.datetime import utc_now
from tools.nuclei.parser import Finding

_TEMPLATE = {
    "origin": "rengine-origin-exposed",
    "vhost": "rengine-default-vhost",
}
_TITLE = {
    "origin": "Origin reachable outside the CDN",
    "vhost": "Address serves a different site by default",
}
_SEVERITY = {"high": Severity.MEDIUM.value, "medium": Severity.LOW.value}


def _evidence(found: OriginFinding) -> str:
    return (
        ", ".join(f"{item.label} matches" for item in found.evidence)
        or "no shared identity recorded"
    )


def origin_finding(found: OriginFinding) -> Finding:
    """One origin-exposure correlation as a finding."""
    address = found.exposed.host or found.exposed.ip or ""
    kind = found.kind if found.kind in _TEMPLATE else "origin"
    names = [sample.host for sample in found.fronted if sample.host]
    behind = names[0] if names else "a name behind the CDN"
    digest = hashlib.sha256(
        f"{Scanner.RENGINE.value}|{_TEMPLATE[kind]}|{address}|{behind}".encode()
    ).hexdigest()

    if kind == "origin":
        description = (
            f"{address} answers directly and serves the same application as {behind} "
            f"behind its CDN. Shared: {_evidence(found)}."
        )
        impact = (
            "Requests sent to the address bypass the CDN or WAF in front of the "
            "hostname."
        )
        remediation = (
            "Restrict the origin to the CDN's ranges, or move it behind an address "
            "that is not published."
        )
    else:
        description = (
            f"{address} serves a different site without a hostname than {behind}. "
            f"Shared: {_evidence(found)}."
        )
        impact = (
            "The default virtual host on this address exposes an application not "
            "reachable through the hostname."
        )
        remediation = "Give the address a default virtual host that serves nothing."

    return Finding(
        fingerprint=digest,
        scanner=Scanner.RENGINE.value,
        template_id=_TEMPLATE[kind],
        template_name=_TITLE[kind],
        template_path=None,
        template_url=None,
        severity=_SEVERITY.get(found.confidence, Severity.LOW.value),
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
