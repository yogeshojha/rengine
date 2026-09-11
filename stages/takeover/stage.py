from __future__ import annotations

import hashlib

from sqlalchemy import select

from shared.definitions.domains import takeover_provider
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import Protocol, Scanner, Severity
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services import vuln_inventory
from shared.utils.datetime import utc_now
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.takeover.config import TakeoverConfig
from tools.nuclei.parser import Finding

logger = get_logger(__name__)

_TEMPLATE = "rengine-dangling-cname"
_CAP = 5000


def _finding(name: str, cname: str, provider: str) -> Finding:
    digest = hashlib.sha256(
        f"{Scanner.RENGINE.value}|{_TEMPLATE}|{name}|{cname}".encode()
    ).hexdigest()
    return Finding(
        fingerprint=digest,
        scanner=Scanner.RENGINE.value,
        template_id=_TEMPLATE,
        template_name="Dangling CNAME to a claimable provider",
        template_path=None,
        template_url=None,
        severity=Severity.MEDIUM.value,
        protocol=Protocol.DNS.value,
        matcher_name=provider,
        extractor_name=None,
        extracted_results=[cname],
        description=(
            f"{name} is a CNAME to {cname}, which is {provider}, and the name resolves "
            "to no address. If the resource behind it has been released, whoever "
            "registers it next serves content on this hostname."
        ),
        impact=(
            "An attacker who claims the released resource controls what this hostname "
            "serves, including cookies and certificates issued for it."
        ),
        remediation=(
            f"Remove the CNAME, or re-claim the resource on {provider} so it is yours."
        ),
        references=[],
        tags=["takeover", "dns"],
        authors=["rengine"],
        cve_ids=[],
        cwe_ids=[],
        cvss_metrics=None,
        cvss_score=None,
        epss_score=None,
        epss_percentile=None,
        cpe=None,
        is_kev=False,
        matched_at=name,
        host=name,
        ip=None,
        port=None,
        scheme=None,
        url=None,
        path=None,
        request=None,
        response=None,
        curl_command=None,
        observed_at=utc_now(),
    )


class TakeoverStage(Stage):
    name = "takeover"
    title = "Subdomain Takeover"
    description = "Report hostnames whose CNAME points at a hosting provider but resolves nowhere."
    phase = Phase.DEPTH.value
    depends_on = frozenset({"subdomain_discovery", "seed_resolution"})
    group = StageGroup.HOSTS.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.HOSTS.value})
    produces = frozenset({AssetKind.VULNERABILITIES.value})
    applies_to = ALL_TARGETS
    touches_target = False
    config_model = TakeoverConfig

    def run(self) -> StageResult:
        self._check_abort()
        rows = (
            self.session.execute(
                select(Subdomain.name, Subdomain.cname, Subdomain.resolved_ips)
                .where(
                    Subdomain.scan_id == self.ctx.scan_id,
                    Subdomain.cname.isnot(None),
                    Subdomain.cname != "",
                    Subdomain.is_excluded.is_(False),
                )
                .limit(_CAP)
            )
        ).all()

        findings: list[Finding] = []
        for name, cname, ips in rows:
            if ips:
                continue
            provider = takeover_provider(cname or "")
            if provider is None:
                continue
            findings.append(_finding(name, cname, provider))

        stored = vuln_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            findings=findings,
        )
        self.session.commit()
        if stored:
            self.publish_results(SurfaceDimension.VULNERABILITIES.value)
            self.emit_progress(
                f"{stored} hostname{'' if stored == 1 else 's'} point at a provider "
                "and resolve nowhere"
            )
        return StageResult(counts={"vulnerabilities": stored, "checked": len(rows)})
