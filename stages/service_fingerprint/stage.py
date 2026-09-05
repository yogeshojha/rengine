from __future__ import annotations

from sqlalchemy import select

from shared.definitions.ports import (
    CDN_EDGE_PORTS,
    PortSource,
    ScanPolicy,
    ServiceClass,
    likely_tls,
)
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.services import port_inventory
from shared.services.port_inventory import ServiceObservation
from shared.services.scope_filter import ip_excluded
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.service_fingerprint.config import ServiceFingerprintConfig
from tools.banner import BannerClient, Endpoint

logger = get_logger(__name__)


class ServiceFingerprintStage(Stage):
    name = "service_fingerprint"
    title = "Service Fingerprint"
    description = (
        "Identify the software behind every non-web port from its service banner."
    )
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"http_probe"})
    group = StageGroup.SERVICES.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.PORTS.value})
    applies_to = ALL_TARGETS
    tools = ()
    config_model = ServiceFingerprintConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        endpoints = self._endpoints(cfg)
        if not endpoints:
            return StageResult(counts={"fingerprinted": 0, "probed": 0})

        client = BannerClient(
            timeout=float(cfg.timeout),
            concurrency=cfg.threads,
            proxy_url=self.net_options().proxy_url,
        )
        self.emit_progress(f"reading banners on {len(endpoints)} ports")
        results = client.probe_all(endpoints)
        self._check_abort()
        if not results:
            self.emit_progress(f"no banner returned by {len(endpoints)} ports")
            return StageResult(counts={"fingerprinted": 0, "probed": len(endpoints)})

        port_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            source=PortSource.BANNER.value,
            keep_source=True,
            observations=[
                ServiceObservation(
                    ip=f.ip,
                    port=f.port,
                    tls=f.tls,
                    service_name=f.service,
                    product=f.product,
                    version=f.version,
                    banner=f.banner,
                )
                for f in results
            ],
        )
        named = sum(1 for f in results if f.product or f.version)
        self.emit_progress(
            f"{len(results)} of {len(endpoints)} ports answered, {named} named a product"
        )
        return StageResult(
            counts={"fingerprinted": len(results), "probed": len(endpoints)}
        )

    def _endpoints(self, cfg: ServiceFingerprintConfig) -> list[Endpoint]:
        # the banner grab is a real connection, so it obeys the port scan's own policy
        query = (
            select(
                Port.ip,
                Port.number,
                Port.service_name,
                Port.tls,
                IpAddress.scan_policy,
            )
            .outerjoin(
                IpAddress,
                (IpAddress.scan_id == Port.scan_id) & (IpAddress.ip == Port.ip),
            )
            .where(
                Port.scan_id == self.ctx.scan_id,
                Port.is_http.is_(False),
                Port.protocol == "tcp",
            )
        )
        if not cfg.include_unknown:
            query = query.where(Port.service_class != ServiceClass.OTHER.value)
        rows = self.session.execute(
            query.order_by(Port.ip, Port.number).limit(cfg.max_services)
        ).all()
        excluded = self.ctx.resolved.excluded_ips or []
        return [
            Endpoint(
                ip=ip, port=number, service=name, tls=bool(tls) or likely_tls(number)
            )
            for ip, number, name, tls, policy in rows
            if _allowed(policy, number) and not (excluded and ip_excluded(ip, excluded))
        ]


def _allowed(policy: str | None, port: int) -> bool:
    if policy == ScanPolicy.SKIP.value:
        return False
    if policy == ScanPolicy.WEB.value:
        return port in CDN_EDGE_PORTS
    return True
