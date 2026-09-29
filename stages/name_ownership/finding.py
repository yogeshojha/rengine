from __future__ import annotations

import hashlib

from shared.definitions.name_ownership import (
    CLAIM_TEMPLATES,
    CLAIM_TITLES,
    ClaimEvidence,
    NameClaim,
)
from shared.definitions.vulnerabilities import Protocol, Scanner, Severity
from shared.services.name_ownership import Claim
from shared.utils.datetime import utc_now
from tools.nuclei.parser import Finding

_SEVERITY = {
    NameClaim.FOREIGN_SITE.value: Severity.HIGH.value,
    NameClaim.UNHOSTED.value: Severity.MEDIUM.value,
}
SEVERITIES: tuple[str, ...] = tuple(set(_SEVERITY.values()))


def _lines(claim: Claim, root: str) -> list[str]:
    network = f" ({claim.asn_org})" if claim.asn_org else ""
    lines = [f"Resolves to: {claim.ip or 'unknown'}{network}"]
    if claim.kind == NameClaim.FOREIGN_SITE.value:
        shown = f"{claim.title} ({claim.domain})" if claim.title else claim.domain
        lines.append(f"Content: {shown}")
    else:
        lines.append(f"Content: {claim.title or 'none'}")
    for kind, value in claim.evidence:
        if kind == ClaimEvidence.REDIRECT.value:
            lines.append(f"Redirect: {value}")
        elif kind == ClaimEvidence.CERTIFICATE.value:
            lines.append(f"Certificate: {value}")
        elif kind == ClaimEvidence.LINKS.value:
            lines.append(f"Links to {claim.domain}: {value}")
        elif kind == ClaimEvidence.ADDRESS_DEFAULT.value:
            lines.append(f"Same response as {value} without a Host header")
    if claim.kind == NameClaim.FOREIGN_SITE.value:
        lines.append(f"References to {root}: none")
    if claim.siblings:
        lines.append(
            f"Same finding on this address: {claim.siblings} more under {root}"
        )
    return lines


def claim_finding(claim: Claim, root: str) -> Finding:
    """One hostname on a third-party server, as a finding."""
    template = CLAIM_TEMPLATES[claim.kind]
    digest = hashlib.sha256(
        f"{Scanner.RENGINE.value}|{template}|{claim.host}|{claim.domain}".encode()
    ).hexdigest()
    if claim.kind == NameClaim.FOREIGN_SITE.value:
        impact = (
            f"Content on {claim.host} is controlled by the operator of {claim.domain}."
        )
    else:
        impact = f"Content on {claim.host} is controlled by the operator of {claim.ip or 'the address'}."
    return Finding(
        fingerprint=digest,
        scanner=Scanner.RENGINE.value,
        template_id=template,
        template_name=CLAIM_TITLES[claim.kind],
        template_path=None,
        template_url=None,
        severity=_SEVERITY[claim.kind],
        protocol=Protocol.HTTP.value,
        matcher_name=claim.domain,
        extractor_name=None,
        extracted_results=[claim.domain, *sorted({k for k, _ in claim.evidence})],
        description="\n".join(_lines(claim, root)),
        impact=impact,
        remediation=f"Remove or update the DNS record for {claim.host}.",
        references=[],
        tags=["takeover", "dns", "stale-record"],
        authors=["rengine"],
        cve_ids=[],
        cwe_ids=[],
        cvss_metrics=None,
        cvss_score=None,
        epss_score=None,
        epss_percentile=None,
        cpe=None,
        is_kev=False,
        matched_at=claim.url or claim.host,
        host=claim.host,
        ip=claim.ip,
        port=claim.port,
        scheme=claim.scheme,
        url=claim.url or None,
        path=None,
        request=None,
        response=None,
        curl_command=None,
        observed_at=utc_now(),
    )
