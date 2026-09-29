from __future__ import annotations

from shared.definitions.default_engine import VULNERABILITY_STAGE
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.services import vuln_inventory
from shared.services.name_ownership import claims
from stages.base import DOMAIN_TARGETS, Stage, StageResult
from stages.name_ownership.config import NameOwnershipConfig
from stages.name_ownership.finding import SEVERITIES, claim_finding


class NameOwnershipStage(Stage):
    name = "name_ownership"
    title = "Hostname Ownership"
    description = "Report hostnames that serve third-party content or resolve to a server with no site for them."
    phase = Phase.DEPTH.value
    depends_on = frozenset({"http_probe", "origin_probe"})
    group = StageGroup.HOSTS.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.HTTP_ASSETS.value})
    produces = frozenset({AssetKind.VULNERABILITIES.value})
    applies_to = DOMAIN_TARGETS
    touches_target = False
    config_model = NameOwnershipConfig
    check_of = VULNERABILITY_STAGE
    finding_severities = SEVERITIES

    def run(self) -> StageResult:
        self._check_abort()
        root = self.ctx.target_value
        found = claims(self.session, self.ctx.scan_id, root, self.ctx.project_id)
        stored = vuln_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            findings=self.selected_findings(
                [claim_finding(claim, root) for claim in found]
            ),
        )
        self.session.commit()
        if stored:
            self.publish_results(SurfaceDimension.VULNERABILITIES.value)
            self.emit_progress(
                f"{stored} hostname{'' if stored == 1 else 's'} on third-party servers"
            )
        return StageResult(counts={"vulnerabilities": stored})
