from __future__ import annotations

import uuid

from shared.definitions.intensity import TransportTool
from shared.definitions.scan_surface import (
    BASE_MAX_DEPTH,
    MAX_BASES_PER_ORIGIN,
    SurfaceClass,
)
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import (
    MAX_FINDINGS_PER_SCAN,
    SEVERITY_LABELS,
    CoverageStatus,
    Severity,
)
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.vulnerability import VulnerabilityCoverage
from shared.services import scan_surface, vuln_inventory
from shared.services.vuln_templates import library_ready
from shared.utils.datetime import utc_now
from stages.base import ALL_TARGETS, Stage, StageAbortedError, StageResult
from stages.dast_scan.config import DastScanConfig
from stages.dast_scan.scanners import scanners
from stages.vulnerability_scan.scanners import Coverage, ScannerContext

logger = get_logger(__name__)


def _unavailable(name: str) -> Coverage:
    return Coverage(
        group=name,
        status=CoverageStatus.SKIPPED.value,
        error=f"{name} is not installed on this instance. None of its checks ran.",
        ended_at=utc_now(),
    )


def _crashed(name: str, exc: Exception) -> Coverage:
    return Coverage(
        group=name,
        status=CoverageStatus.FAILED.value,
        error=str(exc)[:2000],
        ended_at=utc_now(),
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
    tools = ("nuclei",)
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

        index = vuln_inventory.build_index(self.session, self.ctx.scan_id)
        stored: list[str] = []

        def _store(findings: list) -> int:
            self._check_abort()
            room = MAX_FINDINGS_PER_SCAN - len(stored)
            if room <= 0:
                return 0
            written = vuln_inventory.upsert(
                self.session,
                scan_id=self.ctx.scan_id,
                target_id=self.ctx.target_id,
                project_id=self.ctx.project_id,
                findings=findings[:room],
                index=index,
            )
            stored.extend(f.fingerprint for f in findings[:room])
            if written:
                self.publish_results(SurfaceDimension.VULNERABILITIES.value)
                worst = min(
                    (f.severity for f in findings[:room]),
                    key=lambda s: list(SEVERITY_LABELS).index(s),
                    default=Severity.INFO.value,
                )
                self.emit_progress(
                    f"{len(stored)} findings so far, worst is {SEVERITY_LABELS[worst].lower()}"
                )
            return written

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
            on_findings=_store,
            on_marks=_mark,
            on_split=_split,
            on_progress=self.emit_progress,
            is_aborted=self.ctx.is_aborted,
        )

        available = scanners()
        total = 0
        rows: list[VulnerabilityCoverage] = []
        for name in cfg.scanners:
            self._check_abort()
            scanner_cls = available.get(name)
            if scanner_cls is None:
                rows.extend(self._record(name, [_unavailable(name)]))
                continue
            try:
                result = scanner_cls(context).run()
            except StageAbortedError:
                raise
            except Exception as exc:
                logger.warning("fuzzer failed", scanner=name, exc_info=True)
                rows.extend(self._record(name, [_crashed(name, exc)]))
                continue
            total += result.findings
            rows.extend(self._record(name, result.coverage))

        self.session.commit()
        scan_surface.settle(self.session, self.ctx.scan_id)
        _raise_if_broken(rows)
        return StageResult(
            counts={
                "vulnerabilities": total,
                "requests": len(plan.requests),
                "directories": len(plan.bases),
            }
        )

    def _record(
        self, scanner: str, items: list[Coverage]
    ) -> list[VulnerabilityCoverage]:
        stored = []
        for item in items:
            row = VulnerabilityCoverage(
                scan_id=self.ctx.scan_id,
                target_id=self.ctx.target_id,
                project_id=self.ctx.project_id,
                scanner=scanner,
                group=item.group[:120],
                status=item.status,
                tier=item.tier,
                batch=item.batch,
                hosts_covered=item.hosts_covered,
                severities=list(item.severities),
                template_sets=list(item.template_sets),
                templates_selected=item.templates_selected,
                templates_loaded=item.templates_loaded,
                custom_templates=item.custom_templates,
                hosts_total=item.hosts_total,
                hosts_scanned=item.hosts_scanned,
                hosts_dropped=item.hosts_dropped,
                requests_sent=item.requests_sent,
                requests_planned=item.requests_planned,
                matched=item.matched,
                errors=item.errors,
                rate_limit=item.rate_limit,
                concurrency=item.concurrency,
                command=item.command,
                error=item.error,
                started_at=item.started_at,
                ended_at=item.ended_at,
                duration_seconds=item.duration_seconds,
            )
            self.session.add(row)
            stored.append(row)
        return stored


def _raise_if_broken(coverage: list[VulnerabilityCoverage]) -> None:
    """A fuzzer that tried and broke fails the stage."""
    broken = [
        f"{row.scanner}: {row.error or 'failed'}"
        for row in coverage
        if row.status == CoverageStatus.FAILED.value
    ]
    if broken:
        raise RuntimeError("; ".join(broken)[:1000])


__all__ = ["DastScanStage"]
