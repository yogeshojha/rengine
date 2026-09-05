from __future__ import annotations

from sqlalchemy import func, select

from shared.definitions.domains import registrable_domain
from shared.definitions.endpoints import parse_url
from shared.definitions.vulnerabilities import CoverageStatus
from shared.enums.scan import Intensity, Phase
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.endpoint import Endpoint, EndpointCoverage
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.services import endpoint_inventory
from shared.services.scope_filter import matches_any
from shared.utils.datetime import utc_now
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.url_discovery.config import UrlDiscoveryConfig
from stages.url_discovery.providers import URL_PROVIDERS, Host, ProviderContext

logger = get_logger(__name__)

_LIVE_MAX = 400


def _unavailable(source: str, reason: str) -> EndpointCoverage:
    return EndpointCoverage(
        source=source,
        status=CoverageStatus.SKIPPED.value,
        error=reason,
        ended_at=utc_now(),
    )


class UrlDiscoveryStage(Stage):
    name = "url_discovery"
    title = "URL Discovery"
    description = "Collect the URLs and paths that exist on every live web asset."
    phase = Phase.DEPTH.value
    level = 0
    applies_to = ALL_TARGETS
    tools = ("katana", "urlfinder")
    # the stage survives a passive scan; the providers that touch the target are gated below
    touches_target = False
    config_model = UrlDiscoveryConfig
    launch_fields = ("enabled", "providers", "crawl_depth", "max_crawl_minutes")

    def should_run(self) -> bool:
        return self.cfg.enabled and bool(self.cfg.providers)

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg

        seeded = endpoint_inventory.seed_from_assets(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
        )
        hosts = self._hosts()
        if not hosts:
            self.emit_progress("no live web asset to collect urls from")
            return StageResult(counts={"endpoints": seeded.created})

        index = endpoint_inventory.build_index(self.session, self.ctx.scan_id)
        context = ProviderContext(
            session=self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            target_value=self.ctx.target_value,
            target_type=self.ctx.target_type,
            hosts=hosts,
            apex_domains=self._apex_domains(hosts),
            cfg=cfg,
            resolved=self.ctx.resolved,
            net=self.net_options(),
            recorder=self.ctx.recorder,
            on_progress=self.emit_progress,
            is_aborted=self.ctx.is_aborted,
        )

        passive = self.ctx.resolved.intensity == Intensity.PASSIVE.value
        created = seeded.created
        coverage: list[EndpointCoverage] = []
        for source in cfg.providers:
            self._check_abort()
            provider_cls = URL_PROVIDERS.get(source)
            if provider_cls is None:
                coverage.append(
                    _unavailable(source, f"{source} is not a known URL source.")
                )
                continue
            if passive and provider_cls.touches_target:
                coverage.append(
                    _unavailable(
                        source,
                        "This source sends requests to the target, which a passive scan does not allow.",
                    )
                )
                continue

            result = provider_cls(context).run()
            result.observations = self._in_scope(result.observations)
            written = endpoint_inventory.upsert(
                self.session,
                scan_id=self.ctx.scan_id,
                target_id=self.ctx.target_id,
                project_id=self.ctx.project_id,
                source=result.source,
                observations=result.observations,
                index=index,
            )
            created += written.created
            coverage.append(self._coverage(result, written))

        self._store(coverage)
        total = self._total()
        self.emit_progress(f"{total} endpoints across {len(hosts)} web assets")
        return StageResult(counts={"endpoints": total, "endpoints_new": created})

    def _in_scope(self, observations: list) -> list:
        """Drop anything the scan context excluded by path."""
        patterns = self.ctx.resolved.excluded_paths or []
        if not patterns:
            return observations
        kept = []
        for obs in observations:
            parsed = parse_url(obs.url)
            if parsed is not None and matches_any(parsed.path, patterns):
                continue
            kept.append(obs)
        return kept

    def _hosts(self) -> list[Host]:
        rows = self.session.execute(
            select(
                HttpAsset.url,
                HttpAsset.host,
                HttpAsset.port,
                HttpAsset.scheme,
                HttpAsset.status_code,
            ).where(HttpAsset.scan_id == self.ctx.scan_id)
        ).all()
        live = [
            Host(
                url=row.url,
                host=row.host,
                port=int(row.port or 0),
                scheme=row.scheme,
                status_code=row.status_code,
            )
            for row in rows
            if row.status_code is not None and row.status_code < _LIVE_MAX
        ]
        live.sort(key=lambda h: (h.scheme != "https", h.host, h.port))
        return live[: self.cfg.max_hosts]

    def _apex_domains(self, hosts: list[Host]) -> list[str]:
        if self.ctx.target_type == TargetType.DOMAIN.value:
            apex = registrable_domain(self.ctx.target_value)
            if apex:
                return [apex]
        names = (
            self.session.execute(
                select(Subdomain.name).where(Subdomain.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        apexes = {registrable_domain(n) for n in names}
        apexes |= {registrable_domain(h.host) for h in hosts}
        return sorted(a for a in apexes if a)

    def _coverage(self, result, written) -> EndpointCoverage:
        status = result.status
        if status == CoverageStatus.COMPLETED.value and result.capped:
            status = CoverageStatus.PARTIAL.value
        return EndpointCoverage(
            source=result.source,
            tool=result.tool,
            status=status,
            hosts_total=result.hosts_total,
            hosts_scanned=result.hosts_scanned,
            hosts_dropped=list(result.hosts_dropped),
            urls_found=result.urls_found,
            urls_stored=written.created + written.updated,
            pages_fetched=result.pages_fetched,
            depth_reached=result.depth_reached,
            errors=result.errors,
            capped=result.capped,
            cap_reason=result.cap_reason,
            command=result.command,
            error=result.error,
            started_at=result.started_at,
            ended_at=result.ended_at,
            duration_seconds=result.duration_seconds,
        )

    def _store(self, coverage: list[EndpointCoverage]) -> None:
        for row in coverage:
            row.scan_id = self.ctx.scan_id
            row.target_id = self.ctx.target_id
            row.project_id = self.ctx.project_id
            self.session.add(row)
        self.session.commit()

    def _total(self) -> int:
        return int(
            self.session.execute(
                select(func.count())
                .select_from(Endpoint)
                .where(Endpoint.scan_id == self.ctx.scan_id)
            ).scalar_one()
        )
