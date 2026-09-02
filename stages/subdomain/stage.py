from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import delete

from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.api_key import APIProvider
from shared.enums.scan import Phase
from shared.enums.subdomain import SubdomainSource
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services.activity_log import ActivityLogService
from shared.services.api_key.sync_api_key import SyncAPIKeyService
from shared.services.scope_filter import matches_any
from shared.utils.datetime import utc_now
from stages.base import DOMAIN_TARGETS, Stage, StageAbortedError, StageResult
from stages.subdomain.config import PASSIVE_TOOLS, SubdomainConfig
from stages.subdomain.parser import merge_and_filter
from stages.subdomain.providers import (
    PASSIVE_PROVIDERS,
    ProviderContext,
    ProviderResult,
    SubdomainProvider,
)
from tools.dnsx.client import DnsxClient, DnsxError

logger = get_logger(__name__)

_PREFETCH_KEYS = (
    APIProvider.SECURITYTRAILS,
    APIProvider.CHAOS,
    APIProvider.NETLAS,
)
_MAX_CONCURRENCY = 8
_RESOLVE_BATCH_THREADS = 50


class SubdomainStage(Stage):
    name = "subdomain_discovery"
    title = "Subdomain Discovery"
    description = "Enumerate subdomains from passive sources, certificates and bruteforce."
    phase = Phase.EXPANSION.value
    level = 0
    applies_to = DOMAIN_TARGETS
    tools = PASSIVE_TOOLS
    api_keys = tuple(p.value for p in _PREFETCH_KEYS)
    touches_target = False
    config_model = SubdomainConfig

    def should_run(self) -> bool:
        return self.cfg.enabled and bool(self.cfg.enabled_sources or self.cfg.tls_discovery)

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        resolved = self.ctx.resolved
        domain = self.ctx.target_value.strip().lower().rstrip(".")
        activity = ActivityLogService(self.session)

        api_keys = self._prefetch_keys()
        pctx = ProviderContext(
            domain=domain,
            timeout=cfg.tool_timeout(resolved.intensity),
            threads=cfg.dns_threads,
            proxy_url=resolved.proxy_url,
            api_keys=api_keys,
            recorder=self.ctx.recorder,
            tool_options=dict(resolved.tool_options or {}),
        )

        provider_classes = self._select_providers(cfg)
        results = self._run_providers(provider_classes, pctx, activity)
        self._check_abort()

        merged = merge_and_filter(results, domain, resolved.included_subdomains)
        # the target itself is in scope — nothing downstream runs without it
        merged.setdefault(domain, set()).add(SubdomainSource.TARGET.value)
        excluded = {n for n in merged if matches_any(n, resolved.excluded_subdomains)}
        logger.info(
            "subdomain merge for %s: %d unique (%d excluded)",
            domain,
            len(merged),
            len(excluded),
        )

        # excluded subdomains are stored but not resolved or processed further
        to_resolve = [n for n in merged if n not in excluded]
        probe = f"{uuid.uuid4().hex[:12]}.{domain}"
        resolution = self._resolve([*to_resolve, probe], cfg)
        probe_info = resolution.pop(probe, None)
        wildcard_ips = (
            set(probe_info["ips"]) if probe_info and probe_info.get("ips") else set()
        )

        active, ips_seen = self._persist(merged, resolution, wildcard_ips, excluded)

        return StageResult(
            counts={
                "subdomains": len(merged),
                "active": active,
                "ips": len(ips_seen),
                "excluded": len(excluded),
            },
        )

    def _check_abort(self) -> None:
        if self.ctx.is_aborted is not None and self.ctx.is_aborted():
            raise StageAbortedError

    def _prefetch_keys(self) -> dict[str, str | None]:
        svc = SyncAPIKeyService(self.session)
        return {p.value: svc.get_key_for_provider(p) for p in _PREFETCH_KEYS}

    def _select_providers(
        self, cfg: SubdomainConfig
    ) -> list[type[SubdomainProvider]]:
        names = list(dict.fromkeys(cfg.enabled_sources))
        if cfg.tls_discovery and "tlsx" not in names:
            names.append("tlsx")
        selected: list[type[SubdomainProvider]] = []
        for name in names:
            provider = PASSIVE_PROVIDERS.get(name)
            if provider is None:
                logger.warning("unknown subdomain provider '%s', skipping", name)
                continue
            if provider not in selected:
                selected.append(provider)
        return selected

    def _run_providers(
        self,
        provider_classes: list[type[SubdomainProvider]],
        pctx: ProviderContext,
        activity: ActivityLogService,
    ) -> list[ProviderResult]:
        if not provider_classes:
            return []
        results: list[ProviderResult] = []
        workers = min(_MAX_CONCURRENCY, len(provider_classes))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(cls(pctx).run): cls for cls in provider_classes
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                self._log_provider(activity, result)
        return results

    def _log_provider(
        self, activity: ActivityLogService, result: ProviderResult
    ) -> None:
        source = result.source.value
        if result.skipped:
            message = f"{source} skipped — {result.skip_reason}"
            level = ActivityLevel.WARNING
        elif result.error:
            message = f"{source} failed — {result.error}"
            level = ActivityLevel.WARNING
        else:
            message = f"{source} found {result.raw_count} hosts"
            level = ActivityLevel.INFO
        activity.log(
            event=ActivityEvent.SCAN_PROGRESS,
            title="Subdomain discovery",
            description=message,
            level=level,
            project_id=self.ctx.project_id,
            target_id=self.ctx.target_id,
        )
        self.session.commit()
        self.emit_progress(message, source=source)

    def _resolve(self, names: list[str], cfg: SubdomainConfig) -> dict[str, dict]:
        if not names:
            return {}
        try:
            client = DnsxClient(
                timeout=max(120, cfg.tool_timeout(self.ctx.resolved.intensity)),
                threads=max(cfg.dns_threads, _RESOLVE_BATCH_THREADS),
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("dnsx"),
            )
        except DnsxError:
            logger.warning("dnsx unavailable, storing subdomains without resolution")
            return {}

        result = client.query(names, record_types=["a", "aaaa", "cname"])
        out: dict[str, dict] = {}
        for rec in result.json_records:
            host = (rec.get("host") or "").strip().lower().rstrip(".")
            if not host:
                continue
            a = rec.get("a") or []
            aaaa = rec.get("aaaa") or []
            cname_list = rec.get("cname") or []
            ips = [str(x) for x in [*a, *aaaa]]
            cname = str(cname_list[0]) if cname_list else None
            out[host] = {
                "ips": ips,
                "cname": cname,
                "active": bool(ips) or bool(cname),
            }
        return out

    def _persist(
        self,
        merged: dict[str, set[str]],
        resolution: dict[str, dict],
        wildcard_ips: set[str],
        excluded: set[str],
    ) -> tuple[int, set[str]]:
        self.session.execute(
            delete(Subdomain).where(Subdomain.scan_id == self.ctx.scan_id)
        )
        now = utc_now()
        active = 0
        ips_seen: set[str] = set()
        for name, sources in merged.items():
            is_excluded = name in excluded
            info = {} if is_excluded else resolution.get(name, {})
            ips = info.get("ips", [])
            is_active = bool(info.get("active", False))
            if is_active:
                active += 1
            ips_seen.update(ips)
            is_wildcard = bool(ips) and bool(wildcard_ips) and set(ips) <= wildcard_ips
            self.session.add(
                Subdomain(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    name=name,
                    sources=sorted(sources),
                    resolved_ips=ips,
                    cname=info.get("cname"),
                    is_active=is_active,
                    is_wildcard=is_wildcard,
                    is_excluded=is_excluded,
                    discovered_at=now,
                )
            )
        self.session.commit()
        return active, ips_seen
