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


def _facts(claim: Claim) -> list[str]:
    facts: list[str] = []
    for kind, value in claim.evidence:
        if kind == ClaimEvidence.REDIRECT.value:
            facts.append(f"It redirects to {value}.")
        elif kind == ClaimEvidence.CERTIFICATE.value:
            facts.append(f"It presents the certificate for {value}.")
        elif kind == ClaimEvidence.LINKS.value:
            facts.append(f"The page links to {claim.domain} {value} times.")
        elif kind == ClaimEvidence.ADDRESS_DEFAULT.value:
            facts.append(f"{value} returns the same page with no hostname.")
    return facts


def _where(claim: Claim) -> str:
    network = f" ({claim.asn_org})" if claim.asn_org else ""
    return f"{claim.ip}{network}" if claim.ip else "its address"


def claim_finding(claim: Claim, root: str) -> Finding:
    """One owned name answered by another organisation's server, as a finding."""
    template = CLAIM_TEMPLATES[claim.kind]
    digest = hashlib.sha256(
        f"{Scanner.RENGINE.value}|{template}|{claim.host}|{claim.domain}".encode()
    ).hexdigest()
    siblings = (
        f" {claim.siblings} other name{'' if claim.siblings == 1 else 's'} under "
        f"{root} on this address {'does' if claim.siblings == 1 else 'do'} the same."
        if claim.siblings
        else ""
    )
    if claim.kind == NameClaim.FOREIGN_SITE.value:
        shown = f"{claim.title} ({claim.domain})" if claim.title else claim.domain
        description = (
            f"{claim.host} resolves to {_where(claim)} and serves {shown}. "
            f"{' '.join(_facts(claim))} The page does not mention {root}.{siblings}"
        )
        impact = (
            f"The operator of {claim.domain} controls what {claim.host} serves and "
            "can obtain a certificate for it."
        )
    else:
        description = (
            f"{claim.host} resolves to {_where(claim)}, which has no site for it. "
            f"{' '.join(_facts(claim))}{siblings}"
        )
        impact = (
            f"Whoever operates {claim.ip or 'the address'} decides what "
            f"{claim.host} serves."
        )
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
        description=description,
        impact=impact,
        remediation=(
            f"Remove the DNS record for {claim.host}, or point it at a server "
            "that hosts it."
        ),
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
