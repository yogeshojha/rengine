from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from sqlalchemy import select

from shared.definitions.ports import (
    CDN_EDGE_PORTS,
    PortProfile,
    PortSource,
    ScanPolicy,
    profile_ports,
)
from shared.enums.scan import Phase
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from shared.services import ip_inventory, port_inventory
from shared.services.port_inventory import ServiceObservation
from shared.services.scope_filter import ip_excluded
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.port_scan.config import PortScanConfig
from tools.naabu.client import NaabuClient, NaabuError, NaabuOptions, port_args

logger = get_logger(__name__)

CDN_KINDS = ("cdn", "waf")


@dataclass(frozen=True)
class Decision:
    policy: str
    reason: str | None = None


class PortScanStage(Stage):
    name = "port_scan"
    title = "Port Scan"
    description = "Find listening TCP services on every address in scope."
    phase = Phase.EXPANSION.value
    level = 2
    applies_to = ALL_TARGETS
    tools = ("naabu",)
    config_model = PortScanConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        ip_inventory.ensure(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
        )
        rows = self._addresses()
        if not rows:
            return StageResult(counts={"open_ports": 0, "scanned": 0})

        plan = self._plan(rows, cfg)
        self.session.commit()
        full = [ip for ip, d in plan.items() if d.policy == ScanPolicy.FULL.value]
        edge = [ip for ip, d in plan.items() if d.policy == ScanPolicy.WEB.value]
        skipped = len(plan) - len(full) - len(edge)
        if not full and not edge:
            self.emit_progress(f"no address in scope to scan ({skipped} excluded)")
            return StageResult(
                counts={"open_ports": 0, "scanned": 0, "skipped": skipped}
            )

        try:
            client = NaabuClient(
                options=NaabuOptions(
                    rate=cfg.rate,
                    concurrency=cfg.threads,
                    timeout=cfg.timeout,
                    retries=cfg.retries,
                    scan_type=cfg.scan_type,
                    port_threshold=cfg.port_threshold,
                    exclude_ports=cfg.exclude_ports,
                    proxy_url=self.net_options().proxy_url,
                    extra_args=self.ctx.resolved.tool_args("naabu"),
                ),
                recorder=self.ctx.recorder,
            )
        except NaabuError:
            logger.warning("naabu unavailable, skipping port scan")
            return StageResult(counts={"open_ports": 0, "scanned": 0})

        found: list[dict] = []
        failures: list[str] = []
        if full:
            self.emit_progress(f"scanning {len(full)} addresses on {self._label(cfg)}")
            found += self._batch(
                client, full, port_args(cfg.profile, cfg.ports), failures
            )
            self._check_abort()
        if edge:
            self.emit_progress(
                f"probing {len(edge)} CDN-fronted addresses on edge ports"
            )
            edge_ports = ["-p", ",".join(str(p) for p in CDN_EDGE_PORTS)]
            found += self._batch(client, edge, edge_ports, failures)
            self._check_abort()

        count = port_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            source=PortSource.NAABU.value,
            observations=[
                ServiceObservation(
                    ip=item["ip"],
                    port=item["port"],
                    protocol=item["protocol"],
                    tls=item["tls"],
                )
                for item in found
            ],
            replace=True,
        )
        scanned = len(full) + len(edge)
        if failures:
            raise RuntimeError("; ".join(failures))
        self.emit_progress(f"{count} open ports across {scanned} addresses")
        return StageResult(
            counts={
                "open_ports": count,
                "scanned": scanned,
                "edge_only": len(edge),
                "skipped": skipped,
            }
        )

    def _batch(
        self, client: NaabuClient, ips: list[str], flags: list[str], failures: list[str]
    ) -> list[dict]:
        try:
            return client.scan(ips, flags)
        except NaabuError as exc:
            failures.append(str(exc))
            return []

    def _addresses(self) -> list[IpAddress]:
        return list(
            self.session.execute(
                select(IpAddress)
                .where(IpAddress.scan_id == self.ctx.scan_id)
                .order_by(IpAddress.ip)
                .limit(self.cfg.max_addresses)
            )
            .scalars()
            .all()
        )

    def _plan(self, rows: list[IpAddress], cfg: PortScanConfig) -> dict[str, Decision]:
        excluded = self.ctx.resolved.excluded_ips or []
        plan: dict[str, Decision] = {}
        for row in rows:
            decision = self._decide(row, cfg, excluded)
            plan[row.ip] = decision
            row.scan_policy = decision.policy
            row.scan_policy_reason = decision.reason
            self.session.add(row)
        return plan

    @staticmethod
    def _decide(row: IpAddress, cfg: PortScanConfig, excluded: list[str]) -> Decision:
        if excluded and ip_excluded(row.ip, excluded):
            return Decision(ScanPolicy.SKIP.value, "scope")
        if cfg.skip_private and _is_private(row.ip):
            return Decision(ScanPolicy.SKIP.value, "private")
        if row.is_alive is False:
            return Decision(ScanPolicy.SKIP.value, "unreachable")
        kind = row.cdn_type
        if kind in CDN_KINDS:
            policy = ScanPolicy(cfg.cdn_policy).value
            return Decision(policy, "cdn")
        if kind == "cloud" and not cfg.scan_cloud:
            return Decision(ScanPolicy.WEB.value, "cloud")
        return Decision(ScanPolicy.FULL.value, None)

    @staticmethod
    def _label(cfg: PortScanConfig) -> str:
        explicit = profile_ports(cfg.profile)
        if explicit:
            return f"{len(explicit)} ports"
        if cfg.profile == PortProfile.CUSTOM.value:
            return cfg.ports or "the default port set"
        return str(cfg.profile).replace("-", " ")


def _is_private(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not address.is_global
