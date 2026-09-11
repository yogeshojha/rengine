from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import Session

from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import Protocol, Scanner, Severity
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.enums.subdomain import SubdomainSource
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services import vuln_inventory
from shared.utils.datetime import utc_now
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.zone_transfer.config import ZoneTransferConfig
from tools.nuclei.parser import Finding

logger = get_logger(__name__)

_TEMPLATE = "rengine-zone-transfer"
_SAMPLE = 10


def _finding(zone: str, names: list[str]) -> Finding:
    digest = hashlib.sha256(
        f"{Scanner.RENGINE.value}|{_TEMPLATE}|{zone}".encode()
    ).hexdigest()
    shown = ", ".join(names[:_SAMPLE])
    rest = len(names) - _SAMPLE
    if rest > 0:
        shown += f" and {rest:,} more"
    return Finding(
        fingerprint=digest,
        scanner=Scanner.RENGINE.value,
        template_id=_TEMPLATE,
        template_name="DNS zone transfer allowed",
        template_path=None,
        template_url=None,
        severity=Severity.HIGH.value,
        protocol=Protocol.DNS.value,
        matcher_name="axfr",
        extractor_name=None,
        extracted_results=names[:_SAMPLE],
        description=(
            f"A nameserver for {zone} answered an unauthenticated AXFR request with the "
            f"zone's contents. {len(names):,} hostname{'' if len(names) == 1 else 's'} "
            f"came back, including {shown}."
        ),
        impact=(
            "The zone lists every name its owner published, including the internal, "
            "staging and administrative ones no public source indexes. An attacker gets "
            "the whole map in one request, with no scanning and nothing to detect."
        ),
        remediation=(
            "Restrict AXFR on every nameserver for this zone to its own secondaries, by "
            "address or TSIG key, and refuse it from everyone else."
        ),
        references=[],
        tags=["dns", "axfr", "disclosure"],
        authors=["rengine"],
        cve_ids=[],
        cwe_ids=["CWE-200"],
        cvss_metrics=None,
        cvss_score=None,
        epss_score=None,
        epss_percentile=None,
        cpe=None,
        is_kev=False,
        matched_at=zone,
        host=zone,
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


def transferred_names(session: Session, scan_id: uuid.UUID) -> list[str]:
    """A host whose sources name the zone transfer is the record that the zone gave it up."""
    return list(
        session.scalars(
            select(Subdomain.name)
            .where(
                Subdomain.scan_id == scan_id,
                func.jsonb_exists_any(
                    cast(Subdomain.sources, JSONB),
                    pg_array([SubdomainSource.ZONE_TRANSFER.value]),
                ),
            )
            .order_by(Subdomain.name)
        )
    )


class ZoneTransferStage(Stage):
    name = "zone_transfer"
    title = "Zone Transfer"
    description = "Report a zone that handed over its whole contents during discovery."
    phase = Phase.DEPTH.value
    depends_on = frozenset({"subdomain_discovery"})
    group = StageGroup.HOSTS.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.HOSTS.value})
    produces = frozenset({AssetKind.VULNERABILITIES.value})
    applies_to = ALL_TARGETS
    # discovery already asked; this reads what came back
    touches_target = False
    config_model = ZoneTransferConfig

    def run(self) -> StageResult:
        self._check_abort()
        names = transferred_names(self.session, self.ctx.scan_id)
        if not names:
            return StageResult(counts={"vulnerabilities": 0})

        zone = self.ctx.target_value.strip().lower().rstrip(".")
        stored = vuln_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            findings=[_finding(zone, names)],
        )
        self.session.commit()
        if stored:
            self.publish_results(SurfaceDimension.VULNERABILITIES.value)
            self.emit_progress(f"{zone} allows zone transfer: {len(names):,} names")
        return StageResult(counts={"vulnerabilities": stored, "names": len(names)})
