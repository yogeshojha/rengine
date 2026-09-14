"""nuclei in DAST mode over the request items, and the exposure checks under directories."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import and_, select

from shared.definitions.scan_surface import BATCH_MAX_HOSTS, Tier
from shared.definitions.vulnerabilities import (
    DAST_ROOT,
    WEAK_MATCHER_PATHS,
    Protocol,
    TemplateOrigin,
)
from shared.models.vuln_template import TemplateSelection, VulnTemplate
from shared.services.scan_surface import (
    SurfaceItem,
    SurfacePlan,
    batches,
    by_origin,
    chunk,
    cost,
    parse_root,
)
from shared.services.vuln_templates import selection_predicate
from stages.vulnerability_scan.scanners.base import ScannerResult
from stages.vulnerability_scan.scanners.nuclei import (
    Job,
    NucleiScanner,
    _by_lane,
    _deadline,
    _resolve,
)
from tools.nuclei.parser import Finding

_EXPOSURE_SET = "exposure"
_REQUESTS_PER_INVOCATION = 100
_BASE_URL = "{{BaseURL}}"


def dast_templates(session, cfg) -> list[VulnTemplate]:
    """The fuzzing checks: the dast tree, gated by severity and the browser switch."""
    clauses = [
        VulnTemplate.enabled.is_(True),
        VulnTemplate.origin == TemplateOrigin.OFFICIAL.value,
        VulnTemplate.path.startswith(DAST_ROOT),
        VulnTemplate.severity.in_(list(cfg.severities)),
        VulnTemplate.path.notin_(sorted(WEAK_MATCHER_PATHS)),
    ]
    if not cfg.headless:
        clauses.append(VulnTemplate.protocol != Protocol.HEADLESS.value)
    return list(session.execute(select(VulnTemplate).where(and_(*clauses))).scalars())


def exposure_templates(session, cfg) -> list[VulnTemplate]:
    """Exposure checks that probe a path under the input, the ones a directory changes."""
    selection = TemplateSelection(
        severities=list(cfg.severities), template_sets=[_EXPOSURE_SET], headless=False
    )
    rows = session.execute(
        select(VulnTemplate).where(selection_predicate(selection))
    ).scalars()
    return [
        row
        for row in rows
        if row.protocol == Protocol.HTTP.value
        and any(p != _BASE_URL and p.startswith(_BASE_URL) for p in row.paths or [])
    ]


class NucleiDastScanner(NucleiScanner):
    """The same runner, handed request and directory items instead of roots."""

    def run(self) -> ScannerResult:
        ctx = self.ctx
        ok, reason = self.availability()
        if not ok:
            return self.skipped(reason or "scanner unavailable")
        plan: SurfacePlan = ctx.surface
        if not (plan.requests or plan.bases):
            return self.skipped("This scan found no request to fuzz.")

        fuzz = _resolve(dast_templates(ctx.session, ctx.cfg))
        exposure = (
            _resolve(exposure_templates(ctx.session, ctx.cfg))
            if plan.bases
            else _resolve([])
        )
        if not fuzz.paths and not exposure.paths:
            return self.skipped("No fuzzing check in the library matches this plan.")

        lanes = self._schedule_requests(plan, fuzz, exposure)
        if not any(lanes.values()):
            return self.skipped("No fuzzing check applies to what this scan found.")

        result = ScannerResult()
        self._deadline = _deadline(ctx.cfg.max_minutes)
        library = fuzz if fuzz.paths else exposure
        library.rows = [*fuzz.rows, *exposure.rows]
        library.paths = {**fuzz.paths, **exposure.paths}
        self._run_lanes(lanes, library, result)
        self._replay(plan, library, result)
        return result

    def _schedule_requests(
        self, plan: SurfacePlan, fuzz, exposure
    ) -> dict[str, list[Job]]:
        cfg = self.ctx.cfg
        rates = self._rates(plan)
        lanes: dict[str, list[Job]] = {}
        counter: dict[str, int] = {}

        def _push(job: Job) -> None:
            counter[job.lane] = counter.get(job.lane, 0) + 1
            job.batch = counter[job.lane]
            lanes.setdefault(job.lane, []).append(job)

        if fuzz.paths and plan.requests:
            files = fuzz.files(fuzz.rows)
            for lane, wanted in _by_lane(plan.requests, cfg.waf_rate_divisor).items():
                grouped: list[SurfaceItem] = [i for g in by_origin(wanted) for i in g]
                for items in chunk(grouped, _REQUESTS_PER_INVOCATION):
                    _push(
                        Job(
                            tier=Tier.DAST.value,
                            lane=lane,
                            batch=0,
                            items=items,
                            templates=files,
                            rate=rates[lane],
                            dast=True,
                            cost=cost(fuzz.rows),
                        )
                    )
        if exposure.paths and plan.bases:
            files = exposure.files(exposure.rows)
            per_host = cost(exposure.rows)
            for lane, wanted in _by_lane(plan.bases, cfg.waf_rate_divisor).items():
                for items in batches(wanted, per_host, rates[lane]):
                    _push(
                        Job(
                            tier=Tier.BASES.value,
                            lane=lane,
                            batch=0,
                            items=items[:BATCH_MAX_HOSTS],
                            templates=files,
                            rate=rates[lane],
                            cost=per_host,
                        )
                    )
        return lanes

    def _replay_targets(
        self, plan: SurfacePlan, finding: Finding
    ) -> list[tuple[SurfaceItem, str]]:
        """The same request on each web asset the origin stands for."""
        url = finding.url or finding.matched_at
        root = parse_root(url)
        if root is None or "://" not in url:
            return []
        parsed = urlsplit(url)
        out: list[tuple[SurfaceItem, str]] = []
        for member in plan.members_of(root.value):
            netloc = urlsplit(member.value).netloc
            target = urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, ""))
            out.append((member, target))
        return out


__all__ = ["NucleiDastScanner", "dast_templates", "exposure_templates"]
