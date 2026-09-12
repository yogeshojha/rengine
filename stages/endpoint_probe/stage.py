from __future__ import annotations

import uuid
from urllib.parse import urlsplit

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.endpoints import PROBE_COVERAGE_SOURCE, STATIC_CLASSES
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import CoverageStatus
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.endpoint import Endpoint, EndpointCoverage
from shared.models.http_asset import HttpAsset
from shared.services import endpoint_inventory, endpoint_judge
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.endpoint_judge import Fingerprint
from shared.services.scope_filter import matches_any
from shared.utils.datetime import utc_now
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.endpoint_probe.config import EndpointProbeConfig
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)

_WRITE_BATCH = 500
_DEFAULT_PORTS = {"http": 80, "https": 443}


class EndpointProbeStage(Stage):
    """Request discovered URLs, highest attack surface first, within a budget."""

    name = "endpoint_probe"
    title = "Endpoint Verification"
    description = "Request the discovered URLs and record each status."
    phase = Phase.DEPTH.value
    depends_on = frozenset({"url_discovery"})
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
            self.emit_progress("every endpoint carries an observed status")
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

        def _write(batch: list[EndpointObservation]) -> int:
            return endpoint_inventory.verify(
                self.session, scan_id=self.ctx.scan_id, observations=batch
            ).updated

        sink = self.results_sink(
            SurfaceDimension.ENDPOINTS.value, _write, rows=_WRITE_BATCH
        )
        canaries = self._canaries(selected)
        fingerprints: dict = {}
        with client.stream_probe([*canaries, *selected]) as stream:
            for record in stream.records:
                self._check_abort()
                fields = parse_httpx_record(record)
                url = fields.get("url")
                if not url:
                    continue
                owner = canaries.get(url)
                if owner is not None:
                    fingerprints.setdefault(owner, []).append(Fingerprint.of(fields))
                    continue
                sink.add(
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
        sink.close()
        answered = sink.written
        endpoint_judge.store_fingerprints(self.session, fingerprints)
        dropped = endpoint_judge.judge(self.session, self.ctx.scan_id)
        if dropped:
            self.publish_results(SurfaceDimension.ENDPOINTS.value)
        status = (
            CoverageStatus.PARTIAL.value if skipped else CoverageStatus.COMPLETED.value
        )
        reason = (
            f"{skipped} endpoints not requested. Budget of {budget} reached."
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
            dropped=dict(dropped),
        )
        removed = sum(dropped.values())
        self.emit_progress(
            f"verified {len(selected)} endpoints, {answered} answered"
            + (f", {removed} removed as noise" if removed else "")
            + (f", {skipped} left unverified" if skipped else "")
        )
        return StageResult(counts={"endpoints_probed": len(selected)})

    def _pending(self, budget: int) -> list[str]:
        """The unverified endpoints most likely to matter, ranked in the database."""
        flagged = func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0
        novel = (
            func.row_number()
            .over(
                partition_by=Endpoint.family,
                order_by=(Endpoint.depth.asc(), Endpoint.url.asc()),
            )
            .label("in_family")
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
        headroom = budget * 4 if excluded else budget
        rows = self.session.execute(
            select(sub.c.url, sub.c.path)
            .order_by(
                sub.c.flagged.desc(),
                sub.c.has_params.desc(),
                (sub.c.in_family == 1).desc(),
                sub.c.depth.asc(),
                sub.c.url.asc(),
            )
            .limit(headroom)
        ).all()
        if excluded:
            rows = [r for r in rows if not matches_any(r.path, excluded)]
        return [r.url for r in rows[:budget]]

    def _canaries(self, selected: list[str]) -> dict[str, uuid.UUID]:
        """Three URLs no site has, per root the probe will touch, keyed to the root's web asset."""
        wanted: set[tuple[str, str, int]] = set()
        for url in selected:
            try:
                parts = urlsplit(url)
                port = parts.port
            except ValueError:
                continue
            scheme = parts.scheme.lower()
            host = (parts.hostname or "").lower()
            if host:
                wanted.add((scheme, host, port or _DEFAULT_PORTS.get(scheme, 0)))
        if not wanted:
            return {}
        rows = self.session.execute(
            select(
                HttpAsset.id, HttpAsset.scheme, HttpAsset.host, HttpAsset.port
            ).where(
                HttpAsset.scan_id == self.ctx.scan_id,
                HttpAsset.host.in_({h for _, h, _ in wanted}),
            )
        ).all()
        out: dict[str, uuid.UUID] = {}
        for asset_id, scheme, host, port in rows:
            key = (scheme, host.lower(), int(port or _DEFAULT_PORTS.get(scheme, 0)))
            if key not in wanted:
                continue
            for url in endpoint_judge.canary_urls(endpoint_judge.root_of(*key)):
                out[url] = asset_id
        return out

    def _unverified(self) -> int:
        q = select(func.count()).where(
            Endpoint.scan_id == self.ctx.scan_id,
            Endpoint.is_probed.is_(False),
        )
        if self.cfg.skip_static:
            q = q.where(Endpoint.endpoint_class.notin_(tuple(STATIC_CLASSES)))
        return int(self.session.execute(q).scalar_one())

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
        dropped: dict[str, int] | None = None,
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
                errors=None if answered is None else max(0, probed - answered),
                capped=bool(skipped),
                cap_reason=reason,
                urls_dropped=dropped or {},
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
