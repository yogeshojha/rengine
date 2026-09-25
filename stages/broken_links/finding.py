from __future__ import annotations

import hashlib

from shared.definitions.broken_links import (
    FINDING_TAGS,
    KIND_LABELS,
    TEMPLATE_ID,
    TEMPLATE_NAME,
)
from shared.definitions.vulnerabilities import Protocol, Scanner
from shared.services.broken_links import BrokenLink
from shared.utils.datetime import utc_now
from tools.nuclei.parser import Finding


def _lines(link: BrokenLink) -> list[str]:
    kind = KIND_LABELS.get(link.kind, link.kind).lower()
    lines = [
        f"Resource: {link.resource_host} loaded as a {kind}",
        f"Registrable domain: {link.domain}",
        "Domain state: does not resolve, available to register",
    ]
    if link.pages > 1:
        lines.append(f"Embedded on {link.pages} pages")
    for example in link.examples[:5]:
        lines.append(f"Page: {example}")
    return lines


def link_finding(link: BrokenLink) -> Finding:
    """One embedded resource loaded from a buyable domain, as a finding."""
    digest = hashlib.sha256(
        f"{Scanner.RENGINE.value}|{TEMPLATE_ID}|{link.resource_host}|{link.kind}".encode()
    ).hexdigest()
    kind = KIND_LABELS.get(link.kind, link.kind).lower()
    return Finding(
        fingerprint=digest,
        scanner=Scanner.RENGINE.value,
        template_id=TEMPLATE_ID,
        template_name=TEMPLATE_NAME,
        template_path=None,
        template_url=None,
        severity=link.severity,
        protocol=Protocol.HTTP.value,
        matcher_name=link.domain,
        extractor_name=None,
        extracted_results=[link.resource_host, link.domain],
        description="\n".join(_lines(link)),
        impact=(
            f"Registering {link.domain} serves the {kind} at {link.resource_host} "
            f"from {link.page_host}."
        ),
        remediation=(
            f"Remove the reference to {link.resource_host} or host the {kind} on an "
            "owned domain."
        ),
        references=[],
        tags=list(FINDING_TAGS),
        authors=["rengine"],
        cve_ids=[],
        cwe_ids=[],
        cvss_metrics=None,
        cvss_score=None,
        epss_score=None,
        epss_percentile=None,
        cpe=None,
        is_kev=False,
        matched_at=link.page_url or link.page_host,
        host=link.page_host,
        ip=None,
        port=link.page_port,
        scheme=link.page_scheme,
        url=link.page_url or None,
        path=None,
        request=None,
        response=None,
        curl_command=None,
        observed_at=utc_now(),
    )
