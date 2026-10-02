from __future__ import annotations

from shared.definitions.broken_links import KIND_SEVERITY
from shared.definitions.default_engine import VULNERABILITY_STAGE
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.services import vuln_inventory
from shared.services.broken_links import dangling
from shared.utils.text import counted
from stages.base import Stage, StageResult
from stages.broken_links.config import BrokenLinksConfig
from stages.broken_links.finding import link_finding


class BrokenLinksStage(Stage):
    name = "broken_links"
    title = "Broken Link Hijacking"
    description = (
        "Report embedded resources loaded from a domain that can now be registered."
    )
    phase = Phase.DEPTH.value
    depends_on = frozenset({"http_probe"})
    group = StageGroup.HOSTS.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.HTTP_ASSETS.value})
    produces = frozenset({AssetKind.VULNERABILITIES.value})
    touches_target = False
    config_model = BrokenLinksConfig
    check_of = VULNERABILITY_STAGE
    finding_severities = tuple(set(KIND_SEVERITY.values()))

    def run(self) -> StageResult:
        self._check_abort()
        found = dangling(self.session, self.ctx.scan_id, self.ctx.target_value)
        self._check_abort()
        stored = vuln_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            findings=self.selected_findings([link_finding(link) for link in found]),
        )
        self.session.commit()
        if stored:
            self.publish_results(SurfaceDimension.VULNERABILITIES.value)
            self.emit_progress(
                f"{counted(stored, 'broken link')} on a domain available to register"
            )
        return StageResult(counts={"vulnerabilities": stored})
