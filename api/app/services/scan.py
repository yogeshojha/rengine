import copy
import logging
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.proxy import ProxyService
from app.services.scan_context import ScanContextService
from app.services.scan_engine import ScanEngineService
from shared.enums.api_key import APIProvider
from shared.enums.scan import ScanStatus
from shared.models.api_key import APIKey
from shared.models.scan import (
    SCAN_STATUSES,
    Scan,
    ScanCreate,
    ScanDailyCount,
    ScanRead,
    ScanStats,
    ScanStatusCounts,
)
from shared.models.scan_context import VALID_RATE_TOOLS, ScanContext
from shared.models.scan_engine import ScanEngine
from shared.models.scan_preview import (
    PreviewPhase,
    PreviewSummary,
    PreviewTool,
    PreviewToolStatus,
    ScanPreview,
)
from shared.models.target import Target
from shared.services.scan_resolve import (
    MASK,
    ResolvedScanConfig,
    _auth_summary,
    _check_baseline_deferred,
    _mask_auth,
    merge_engine_context,
)
from shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)

# TODO(api-keys): expand APIProvider to cover these providers.
CAPABILITY_API_KEYS = {
    "subdomain_securitytrails": "securitytrails",
    "subdomain_censys": "censys",
    "subdomain_virustotal": "virustotal",
    "subdomain_chaos": "chaos",
    "subdomain_binaryedge": "binaryedge",
    "port_scan_passive_shodan": "shodan",
}

_SPEC_RATE_TOOL = 2
_SPEC_THREADS_KEY = 3
_SPEC_TIMEOUT_KEY = 4

_PHASE_TOOLS = {
    "discovery": (
        "Discovery",
        [
            ("related_domains_enabled", "Related Domains"),
            ("org_whois_search", "Org WHOIS Search"),
            ("org_cert_transparency", "Org Cert Transparency"),
            ("org_asn_lookup", "Org ASN Lookup"),
            ("ip_reverse_dns", "IP Reverse DNS"),
            ("ip_vhost_discovery", "IP VHost Discovery"),
        ],
    ),
    "expansion": (
        "Expansion",
        [
            ("subdomain_passive", "Passive Subdomain Enum"),
            ("subdomain_securitytrails", "SecurityTrails"),
            ("subdomain_censys", "Censys"),
            ("subdomain_virustotal", "VirusTotal"),
            ("subdomain_chaos", "Chaos"),
            ("subdomain_binaryedge", "BinaryEdge"),
            ("subdomain_active", "Active Subdomain Brute"),
            ("subdomain_permutation", "Permutations"),
            ("subdomain_takeover", "Subdomain Takeover"),
            ("port_scan_enabled", "Port Scan", "naabu"),
            ("port_scan_passive_shodan", "Shodan Port Scan"),
            ("nmap_enabled", "Nmap"),
            ("http_crawl", "HTTP Crawl"),
            ("tech_detection", "Tech Detection"),
            (
                "screenshot",
                "Screenshot",
                None,
                "screenshot_threads",
                "screenshot_timeout",
            ),
            ("waf_detection", "WAF Detection"),
            ("cdn_detection", "CDN Detection"),
        ],
    ),
    "depth": (
        "Depth",
        [
            (
                "dir_fuzz_enabled",
                "Directory Fuzzing",
                "ffuf",
                "dir_fuzz_threads",
                "dir_fuzz_timeout",
            ),
            ("url_discovery_enabled", "URL Discovery", None, "url_threads"),
            ("js_secret_scan", "JS Secret Scan"),
            ("param_discovery", "Param Discovery"),
            (
                "nuclei_enabled",
                "Nuclei",
                "nuclei",
                "nuclei_concurrency",
                "nuclei_timeout",
            ),
            ("dalfox_enabled", "Dalfox (XSS)"),
            ("crlfuzz_enabled", "CRLFuzz"),
            ("sqlmap_enabled", "SQLMap"),
            ("ssrf_enabled", "SSRF"),
            ("cors_check", "CORS Check"),
            ("ssl_tls_analysis", "SSL/TLS Analysis"),
            ("bypass_403", "403 Bypass"),
            ("graphql_detection", "GraphQL Detection"),
            ("report_enabled", "Reporting"),
        ],
    ),
}

_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60


def _mask_config_headers(config: dict) -> dict:
    out = copy.deepcopy(config)
    headers = out.get("headers") or {}
    out["headers"] = {
        name: (MASK if value else value) for name, value in headers.items()
    }

    depth = (out.get("phases") or {}).get("depth")
    if isinstance(depth, dict) and depth.get("report_webhook_url"):
        depth["report_webhook_url"] = MASK
    return out


def _scan_duration(scan: Scan) -> float | None:
    if scan.started_at is None:
        return None
    end = scan.completed_at or (
        utc_now() if scan.status == ScanStatus.RUNNING.value else None
    )
    if end is None:
        return None
    return round((end - scan.started_at).total_seconds(), 1)


def _human_duration(seconds: int) -> str:
    if seconds < _SECONDS_PER_MINUTE:
        return f"{seconds}s"
    minutes = seconds // _SECONDS_PER_MINUTE
    if minutes < _MINUTES_PER_HOUR:
        return f"{minutes}m"
    hours = minutes // _MINUTES_PER_HOUR
    rem = minutes % _MINUTES_PER_HOUR
    return f"{hours}h {rem}m" if rem else f"{hours}h"


class ScanService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.engine_service = ScanEngineService(session)
        self.context_service = ScanContextService(session)

    async def _get_engine(self, engine_id: UUID, project_id: UUID) -> ScanEngine:
        result = await self.session.execute(
            select(ScanEngine).where(
                ScanEngine.id == engine_id, ScanEngine.project_id == project_id
            )
        )
        engine = result.scalar_one_or_none()
        if not engine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan engine not found"
            )
        return engine

    async def _get_context(self, context_id: UUID, project_id: UUID) -> ScanContext:
        result = await self.session.execute(
            select(ScanContext).where(
                ScanContext.id == context_id, ScanContext.project_id == project_id
            )
        )
        ctx = result.scalar_one_or_none()
        if not ctx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan context not found"
            )
        return ctx

    async def _get_target(self, target_id: UUID, project_id: UUID) -> Target:
        result = await self.session.execute(
            select(Target).where(
                Target.id == target_id, Target.project_id == project_id
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Target not found"
            )
        return target

    async def _resolve_and_validate(self, data: ScanCreate, project_id: UUID):
        engine = await self._get_engine(data.engine_id, project_id)
        context = None
        if data.context_id is not None:
            context = await self._get_context(data.context_id, project_id)
        target = await self._get_target(data.target_id, project_id)

        if context is not None:
            _check_baseline_deferred(
                context.compare_baseline_scan_id, context.scan_only_new_assets
            )

        proxy_url = None
        if context is not None and context.proxy_id is not None:
            proxy_url = await ProxyService(self.session).resolve_proxy_url(
                context.proxy_id
            )

        resolved = merge_engine_context(
            engine,
            context,
            target.target_value,
            target.target_type.value,
            proxy_url=proxy_url,
        )
        return engine, context, target, resolved

    async def _configured_providers(self) -> set[str]:
        result = await self.session.execute(
            select(APIKey).where(APIKey.is_enabled == True)  # noqa: E712
        )
        configured = set()
        for key in result.scalars().all():
            provider = (
                key.provider.value
                if isinstance(key.provider, APIProvider)
                else key.provider
            )
            configured.add(provider)
        return configured

    async def preview(self, data: ScanCreate, project_id: UUID) -> ScanPreview:
        engine, context, target, resolved = await self._resolve_and_validate(
            data, project_id
        )
        configured = await self._configured_providers()

        warnings: list[str] = []
        phases: list[PreviewPhase] = []

        for phase_key, (label, tools) in _PHASE_TOOLS.items():
            phase_dict = resolved.phases.get(phase_key, {})
            preview_tools: list[PreviewTool] = []
            for spec in tools:
                capability = spec[0]
                tool_label = spec[1]
                rate_tool = (
                    spec[_SPEC_RATE_TOOL] if len(spec) > _SPEC_RATE_TOOL else None
                )
                threads_key = (
                    spec[_SPEC_THREADS_KEY] if len(spec) > _SPEC_THREADS_KEY else None
                )
                timeout_key = (
                    spec[_SPEC_TIMEOUT_KEY] if len(spec) > _SPEC_TIMEOUT_KEY else None
                )

                enabled = bool(phase_dict.get(capability, False))
                if not enabled:
                    preview_tools.append(
                        PreviewTool(
                            capability=capability,
                            label=tool_label,
                            status=PreviewToolStatus.SKIPPED_DISABLED,
                            reason="Disabled in engine.",
                        )
                    )
                    continue

                provider = CAPABILITY_API_KEYS.get(capability)
                if provider is not None and provider not in configured:
                    preview_tools.append(
                        PreviewTool(
                            capability=capability,
                            label=tool_label,
                            status=PreviewToolStatus.SKIPPED_NEEDS_KEY,
                            reason=f"{tool_label} skipped — API key not configured.",
                        )
                    )
                    warnings.append(f"{tool_label} skipped — API key not configured.")
                    continue

                rate = (
                    resolved.per_tool_rate_limits.get(rate_tool) if rate_tool else None
                )
                threads = (
                    resolved.resolved_threads.get(threads_key) if threads_key else None
                )
                timeout = (
                    resolved.resolved_timeouts.get(timeout_key) if timeout_key else None
                )
                preview_tools.append(
                    PreviewTool(
                        capability=capability,
                        label=tool_label,
                        status=PreviewToolStatus.WILL_RUN,
                        rate=rate,
                        threads=threads,
                        timeout=timeout,
                    )
                )
            phases.append(
                PreviewPhase(phase=phase_key, label=label, tools=preview_tools)
            )

        will_run = sum(
            1 for p in phases for t in p.tools if t.status == PreviewToolStatus.WILL_RUN
        )
        est_seconds = will_run * _SECONDS_PER_MINUTE
        rates = resolved.per_tool_rate_limits
        rate_summary = ", ".join(
            f"{tool} {rates.get(tool)}/s" for tool in VALID_RATE_TOOLS
        )
        if resolved.global_rate_limit_ceiling is not None:
            rate_summary += f" (ceiling {resolved.global_rate_limit_ceiling}/s)"

        auth = context.auth if context is not None else {"auth_type": "none"}
        extra_headers = context.extra_headers if context is not None else []
        custom_header_names = [
            h.get("name") for h in (extra_headers or []) if h.get("name")
        ]

        proxy_name = None
        if context is not None and context.proxy_id is not None:
            try:
                proxy_name = (
                    await ProxyService(self.session).get(context.proxy_id)
                ).name
            except HTTPException:
                proxy_name = None

        summary = PreviewSummary(
            auth_summary=_auth_summary(auth, extra_headers),
            custom_header_names=custom_header_names,
            rate_summary=rate_summary,
            thread_multiplier=resolved.thread_multiplier,
            timeout_multiplier=resolved.timeout_multiplier,
            http_protocol=resolved.http_protocol,
            follow_redirects=resolved.follow_redirects,
            excluded_subdomains_count=len(resolved.excluded_subdomains),
            excluded_paths_count=len(resolved.excluded_paths),
            excluded_ips_count=len(resolved.excluded_ips),
            excluded_subdomains=resolved.excluded_subdomains,
            excluded_paths=resolved.excluded_paths,
            excluded_ips=resolved.excluded_ips,
            included_subdomains=resolved.included_subdomains,
            proxy_name=proxy_name,
            estimated_duration_seconds=est_seconds,
            estimated_duration_human=_human_duration(est_seconds),
        )

        return ScanPreview(
            target_id=target.id,
            target_value=target.target_value,
            target_type=target.target_type.value,
            engine_id=engine.id,
            engine_name=engine.name,
            context_id=context.id if context is not None else None,
            context_name=context.name if context is not None else None,
            phases=phases,
            summary=summary,
            warnings=warnings,
        )

    async def create(
        self, data: ScanCreate, project_id: UUID, created_by: UUID
    ) -> ScanRead:
        engine, context, target, resolved = await self._resolve_and_validate(
            data, project_id
        )

        execution_config = resolved.model_dump()
        execution_config["_auth_header_names"] = list(resolved._auth_header_names)
        execution_config["_auth"] = (
            _mask_auth(context.auth) if context is not None else {"auth_type": "none"}
        )
        logger.info(
            "Creating scan for target=%s engine=%s header_names=%s",
            target.id,
            engine.id,
            list(resolved.headers.keys()),
        )

        scan = Scan(
            project_id=project_id,
            target_id=target.id,
            engine_id=engine.id,
            engine_name=engine.name,
            context_id=context.id if context is not None else None,
            context_name=context.name if context is not None else None,
            execution_config=execution_config,
            status=ScanStatus.PENDING.value,
            subdomains_found=0,
            ips_found=0,
            open_ports_found=0,
            vulnerabilities_found=0,
            endpoints_found=0,
            created_by=created_by,
        )
        self.session.add(scan)
        await self.session.commit()
        await self.session.refresh(scan)

        await self.engine_service.touch(engine.id, project_id)
        if context is not None:
            await self.context_service.touch(context.id, project_id, scan_id=scan.id)

        self._dispatch_scan(scan)
        return self._to_read(scan)

    def _dispatch_scan(self, scan: Scan) -> None:
        from shared.services.celery_dispatch import dispatch_scan_run  # noqa: PLC0415

        dispatch_scan_run(str(scan.id))

    async def list(
        self,
        project_id: UUID,
        target_id: UUID | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ScanRead]:
        query = select(Scan).where(Scan.project_id == project_id)
        if target_id is not None:
            query = query.where(Scan.target_id == target_id)
        if status is not None:
            query = query.where(Scan.status == status)
        query = query.order_by(Scan.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        scans = result.scalars().all()
        return [self._to_read(s) for s in scans]

    async def stats(self, project_id: UUID, target_id: UUID | None = None) -> ScanStats:
        conds = [Scan.project_id == project_id]
        if target_id is not None:
            conds.append(Scan.target_id == target_id)

        status_rows = (
            await self.session.execute(
                select(Scan.status, func.count()).where(*conds).group_by(Scan.status)
            )
        ).all()
        counts = dict.fromkeys(SCAN_STATUSES, 0)
        total = 0
        for st, n in status_rows:
            if st in counts:
                counts[st] = n
            total += n

        last_scan_at = (
            await self.session.execute(select(func.max(Scan.created_at)).where(*conds))
        ).scalar_one_or_none()

        avg_duration = (
            await self.session.execute(
                select(
                    func.avg(func.extract("epoch", Scan.completed_at - Scan.started_at))
                ).where(
                    *conds,
                    Scan.status == ScanStatus.COMPLETED.value,
                    Scan.started_at.is_not(None),
                    Scan.completed_at.is_not(None),
                )
            )
        ).scalar_one_or_none()

        finished = (
            counts[ScanStatus.COMPLETED.value]
            + counts[ScanStatus.FAILED.value]
            + counts[ScanStatus.CANCELLED.value]
        )
        success_rate = (
            counts[ScanStatus.COMPLETED.value] / finished if finished else None
        )

        start = (utc_now() - timedelta(days=29)).date()
        daily_rows = (
            await self.session.execute(
                select(func.date(Scan.created_at), func.count())
                .where(*conds, func.date(Scan.created_at) >= start)
                .group_by(func.date(Scan.created_at))
            )
        ).all()
        by_day = {str(d): n for d, n in daily_rows}
        daily = [
            ScanDailyCount(
                date=(d := (start + timedelta(days=i)).isoformat()),
                count=by_day.get(d, 0),
            )
            for i in range(30)
        ]

        return ScanStats(
            total=total,
            running=counts[ScanStatus.RUNNING.value],
            by_status=ScanStatusCounts(**counts),
            last_scan_at=last_scan_at,
            avg_duration_seconds=(
                round(avg_duration, 1) if avg_duration is not None else None
            ),
            success_rate=round(success_rate, 3) if success_rate is not None else None,
            daily=daily,
        )

    async def get(self, id: UUID, project_id: UUID) -> ScanRead:
        scan = await self._get_scan(id, project_id)
        return self._to_read(scan)

    async def _get_scan(self, id: UUID, project_id: UUID) -> Scan:
        result = await self.session.execute(
            select(Scan).where(Scan.id == id, Scan.project_id == project_id)
        )
        scan = result.scalar_one_or_none()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
            )
        return scan

    async def cancel(self, id: UUID, project_id: UUID) -> ScanRead:
        scan = await self._get_scan(id, project_id)
        if scan.status in (ScanStatus.PENDING.value, ScanStatus.RUNNING.value):
            scan.status = ScanStatus.CANCELLED.value
            scan.completed_at = utc_now()
            scan.error = "Cancelled by user."
            await self.session.commit()
            await self.session.refresh(scan)
        return self._to_read(scan)

    async def delete(self, id: UUID, project_id: UUID) -> None:
        scan = await self._get_scan(id, project_id)
        await self.session.delete(scan)
        await self.session.commit()

    def _to_read(self, scan: Scan) -> ScanRead:
        cfg = copy.deepcopy(scan.execution_config or {})
        cfg.pop("_auth_header_names", None)
        auth = cfg.pop("_auth", None) or {"auth_type": "none"}
        masked = _mask_config_headers(cfg)
        resolved = ResolvedScanConfig(**masked)
        return ScanRead(
            id=scan.id,
            project_id=scan.project_id,
            target_id=scan.target_id,
            engine_id=scan.engine_id,
            engine_name=scan.engine_name,
            context_id=scan.context_id,
            context_name=scan.context_name,
            execution_config=resolved,
            auth_summary=_auth_summary(auth, list(masked.get("headers", {}).keys())),
            status=scan.status,
            subdomains_found=scan.subdomains_found,
            ips_found=scan.ips_found,
            open_ports_found=scan.open_ports_found,
            vulnerabilities_found=scan.vulnerabilities_found,
            endpoints_found=scan.endpoints_found,
            error=scan.error,
            created_by=scan.created_by,
            created_at=scan.created_at,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            duration_seconds=_scan_duration(scan),
        )
