from __future__ import annotations

import uuid

from shared.definitions.intensity import TransportTool
from shared.definitions.scan_surface import (
    BASE_MAX_DEPTH,
    BUDGET_NOTE,
    MAX_BASES_PER_ORIGIN,
    SurfaceClass,
)
from shared.definitions.vulnerabilities import CoverageStatus
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.models.vulnerability import VulnerabilityCoverage
from shared.services import scan_surface
from shared.services.vuln_templates import library_ready
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.dast_scan.config import DastScanConfig
from stages.dast_scan.scanners import scanners
from stages.vulnerability_scan.scanners import ScannerContext
from stages.vulnerability_scan.stage import (
    FindingStore,
    cap_warnings,
    raise_if_broken,
    run_scanners,
)


class DastScanStage(Stage):
    name = "dast_scan"
    title = "Fuzzing"
    description = (
        "Send payloads to the parameters and directories this scan discovered."
    )
    phase = Phase.DEPTH.value
    depends_on = frozenset({"endpoint_probe", "waf_detect", "vulnerability_scan"})
    group = StageGroup.VULNERABILITIES.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.ENDPOINTS.value, AssetKind.HTTP_ASSETS.value})
    produces = frozenset({AssetKind.VULNERABILITIES.value})
    applies_to = ALL_TARGETS
    tools = ("nuclei", "dalfox", "httpx")
    transport_tool = TransportTool.NUCLEI.value
    rate_weight = 1 / 3
    touches_target = True
    config_model = DastScanConfig
    launch_fields = ("enabled", "severities", "directories", "headless", "max_minutes")

    def should_run(self) -> bool:
        return self.cfg.enabled and bool(self.cfg.scanners)

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        if not library_ready(self.session):
            msg = "The check library is empty. Run a vulnerability scan first or sync the library."
            raise RuntimeError(msg)

        plan = scan_surface.build_requests(
            self.session,
            scan_id=self.ctx.scan_id,
            resolved=self.ctx.resolved,
            max_per_origin=cfg.max_requests_per_origin,
            max_total=cfg.max_requests,
            bases=cfg.directories,
            max_bases_per_origin=MAX_BASES_PER_ORIGIN,
            base_depth=BASE_MAX_DEPTH,
        )
        scan_surface.write(
            self.session,
            plan,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            classes=(SurfaceClass.REQUEST.value, SurfaceClass.BASE.value),
        )
        if not (plan.requests or plan.bases):
            self.emit_progress("no request with parameters to fuzz")
            return StageResult(counts={"vulnerabilities": 0, "requests": 0})
        self.emit_progress(
            f"{len(plan.requests)} requests and {len(plan.bases)} directories to fuzz"
        )

        store = FindingStore(self)

        def _mark(item_ids: list[uuid.UUID], tier: str, status: str, batch) -> None:
            scan_surface.mark(
                self.session, item_ids, tier=tier, status=status, batch=batch
            )

        def _split(item_ids: list[uuid.UUID], note: str) -> None:
            scan_surface.split_members(self.session, item_ids, note)

        context = ScannerContext(
            session=self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            cfg=cfg,
            transport=self.transport,
            resolved=self.ctx.resolved,
            net=self.net_options(),
            surface=plan,
            selection=None,
            recorder=self.ctx.recorder,
            on_findings=store,
            on_marks=_mark,
            on_split=_split,
            on_progress=self.emit_progress,
            is_aborted=self.ctx.is_aborted,
        )

        total, rows = run_scanners(self, context, cfg.scanners, scanners())

        self.session.commit()
        scan_surface.settle(self.session, self.ctx.scan_id)
        raise_if_broken(rows)
        warnings = cap_warnings(store.capped) + _budget_warnings(rows)
        return StageResult(
            counts={
                "vulnerabilities": total,
                "requests": len(plan.requests),
                "directories": len(plan.bases),
            },
            warnings=warnings,
            partial=bool(warnings),
        )


def _budget_warnings(coverage: list[VulnerabilityCoverage]) -> list[str]:
    """A warning when the time budget cut fuzzing short."""
    cut = any(
        row.status == CoverageStatus.SKIPPED.value and row.error == BUDGET_NOTE
        for row in coverage
    )
    return ["Fuzzing did not finish within the time budget."] if cut else []


__all__ = ["DastScanStage"]
