from __future__ import annotations

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.endpoints import PROBE_COVERAGE_SOURCE, STATIC_CLASSES
from shared.definitions.vulnerabilities import CoverageStatus
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.endpoint import Endpoint, EndpointCoverage
from shared.services import endpoint_inventory
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.scope_filter import matches_any
from shared.utils.datetime import utc_now
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.endpoint_probe.config import EndpointProbeConfig
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)


class EndpointProbeStage(Stage):
    """Turn discovered URLs into observed ones, spending a bounded request budget first on
    what carries attack surface."""

    name = "endpoint_probe"
    title = "Endpoint Verification"
    description = (
        "Request the discovered URLs so a status is an observation, not a guess."
    )
    phase = Phase.DEPTH.value
    level = 1
    group = StageGroup.ENDPOINTS.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.ENDPOINTS.value})
    applies_to = ALL_TARGETS
    tools = ("httpx",)
    config_model = EndpointProbeConfig
    launch_fields = ("enabled", "max_urls")

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        started = utc_now()
        budget = cfg.max_urls
        pending = self._pending(budget)
        if not pending:
            self._store(started, 0, 0, 0, CoverageStatus.COMPLETED.value, None, None)
            self.emit_progress("every endpoint already carries an observed status")
            return StageResult(counts={"endpoints_probed": 0})

        selected = pending
        unverified = self._unverified()
        skipped = max(0, unverified - len(selected))

        try:
            client = HttpxClient(
                rate_limit=cfg.rate,
                threads=cfg.threads,
                timeout=cfg.timeout,
                proxy_url=self.net_options().proxy_url,
                headers=self.net_options().headers,
                follow_redirects=cfg.follow_redirects,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("httpx"),
            )
        except HttpxError as e:
            self._store(
                started,
                unverified,
                0,
                skipped,
                CoverageStatus.SKIPPED.value,
                str(e)[:2000],
                None,
            )
            logger.warning("httpx unavailable, endpoints stay unverified")
            return StageResult(counts={"endpoints_probed": 0})

        observations: list[EndpointObservation] = []
        with client.stream_probe(selected) as records:
            for record in records:
                self._check_abort()
                fields = parse_httpx_record(record)
                url = fields.get("url")
                if not url:
                    continue
                observations.append(
                    EndpointObservation(
                        url=url,
                        is_probed=True,
                        status_code=fields.get("status_code"),
                        content_type=fields.get("content_type"),
                        content_length=fields.get("content_length"),
                        title=fields.get("title"),
                        words=fields.get("words"),
                        lines=fields.get("lines"),
                        response_time=fields.get("response_time"),
                        redirect_location=fields.get("location"),
                        content_hash=fields.get("content_hash"),
                        tech=list(fields.get("tech") or []),
                        methods=[fields["method"]] if fields.get("method") else [],
                    )
                )

        # verify(), never upsert(): requesting an endpoint confirms it, it does not
        # discover it, so this must not add a source to the row
        written = endpoint_inventory.verify(
            self.session, scan_id=self.ctx.scan_id, observations=observations
        )
        answered = written.updated
        status = (
            CoverageStatus.PARTIAL.value if skipped else CoverageStatus.COMPLETED.value
        )
        reason = (
            f"{skipped} endpoints were not requested because the budget of {budget} was reached."
            if skipped
            else None
        )
        self._store(
            started,
            unverified,
            len(selected),
            skipped,
            status,
            None,
            reason,
            answered=answered,
        )
        self.emit_progress(
            f"verified {len(selected)} endpoints, {answered} answered"
            + (f", {skipped} left unverified" if skipped else "")
        )
        return StageResult(counts={"endpoints_probed": len(selected)})

    def _pending(self, budget: int) -> list[str]:
        """The unverified endpoints most likely to matter, ranked in the database.

        Ranking in Python meant loading every unverified row first, which on a large
        scan is hundreds of thousands of them.
        """
        flagged = func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0
        # one per directory first, so a wide surface is sampled before a deep one is exhausted
        novel = (
            func.row_number()
            .over(
                partition_by=(Endpoint.host, Endpoint.dir_path),
                order_by=(Endpoint.depth.asc(), Endpoint.url.asc()),
            )
            .label("in_dir")
        )
        ranked = select(
            Endpoint.url.label("url"),
            Endpoint.path.label("path"),
            flagged.label("flagged"),
            (Endpoint.param_count > 0).label("has_params"),
            novel,
            Endpoint.depth.label("depth"),
        ).where(
            Endpoint.scan_id == self.ctx.scan_id,
            Endpoint.is_probed.is_(False),
        )
        if self.cfg.skip_static:
            ranked = ranked.where(Endpoint.endpoint_class.notin_(tuple(STATIC_CLASSES)))
        sub = ranked.subquery()

        excluded = self.ctx.resolved.excluded_paths or []
        # over-fetch so path exclusions applied in Python cannot starve the budget
        headroom = budget * 4 if excluded else budget
        rows = self.session.execute(
            select(sub.c.url, sub.c.path)
            .order_by(
                sub.c.flagged.desc(),
                sub.c.has_params.desc(),
                (sub.c.in_dir == 1).desc(),
                sub.c.depth.asc(),
                sub.c.url.asc(),
            )
            .limit(headroom)
        ).all()
        if excluded:
            rows = [r for r in rows if not matches_any(r.path, excluded)]
        return [r.url for r in rows[:budget]]

    def _unverified(self) -> int:
        return int(
            self.session.execute(
                select(func.count()).where(
                    Endpoint.scan_id == self.ctx.scan_id,
                    Endpoint.is_probed.is_(False),
                )
            ).scalar_one()
        )

    def _store(
        self,
        started,
        total: int,
        probed: int,
        skipped: int,
        status: str,
        error: str | None,
        reason: str | None,
        answered: int | None = None,
    ) -> None:
        ended = utc_now()
        self.session.add(
            EndpointCoverage(
                scan_id=self.ctx.scan_id,
                target_id=self.ctx.target_id,
                project_id=self.ctx.project_id,
                source=PROBE_COVERAGE_SOURCE,
                tool="httpx",
                status=status,
                hosts_total=self._hosts(),
                urls_found=total,
                urls_probed=probed,
                urls_stored=answered,
                # requested and got nothing back: not the same as never requested
                errors=None if answered is None else max(0, probed - answered),
                capped=bool(skipped),
                cap_reason=reason,
                error=error,
                started_at=started,
                ended_at=ended,
                duration_seconds=round((ended - started).total_seconds(), 2),
            )
        )
        self.session.commit()

    def _hosts(self) -> int:
        return int(
            self.session.execute(
                select(func.count(func.distinct(Endpoint.host))).where(
                    Endpoint.scan_id == self.ctx.scan_id
                )
            ).scalar_one()
        )
