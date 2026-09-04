from __future__ import annotations

from sqlalchemy import select

from shared.definitions.ports import DEFAULT_WEB_PORTS, ServiceClass
from shared.enums.scan import Phase
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.services.scope_filter import ip_excluded
from shared.utils.datetime import utc_now
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.origin_probe.config import OriginProbeConfig
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)

_HTTP_FIELDS = set(HttpAsset.model_fields)


class OriginProbeStage(Stage):
    name = "origin_probe"
    title = "Origin Probe"
    description = "Request each address by IP to see what it serves without a hostname."
    phase = Phase.EXPANSION.value
    level = 4
    applies_to = ALL_TARGETS
    tools = ("httpx",)
    config_model = OriginProbeConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        net = self.net_options()
        targets = self._targets(cfg)
        if not targets:
            return StageResult(counts={"probed": 0, "answered": 0})

        try:
            client = HttpxClient(
                rate_limit=cfg.rate,
                threads=cfg.threads,
                timeout=cfg.timeout,
                proxy_url=net.proxy_url,
                headers=net.headers,
                follow_redirects=False,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("httpx"),
            )
        except HttpxError:
            logger.warning("httpx unavailable, skipping origin probe")
            return StageResult(counts={"probed": 0, "answered": 0})

        self.emit_progress(f"requesting {len(targets)} addresses without a hostname")
        with client.stream_probe(targets) as records:
            answered = self._persist(records)
        self.emit_progress(f"{answered} of {len(targets)} answered by address alone")
        return StageResult(counts={"probed": len(targets), "answered": answered})

    def _targets(self, cfg: OriginProbeConfig) -> list[str]:
        rows = self.session.execute(
            select(Port.ip, Port.number)
            .where(
                Port.scan_id == self.ctx.scan_id,
                Port.protocol == "tcp",
                (Port.is_http.is_(True))
                | (Port.service_class == ServiceClass.WEB.value),
            )
            .order_by(Port.ip, Port.number)
        ).all()
        excluded = self.ctx.resolved.excluded_ips or []
        by_ip: dict[str, list[int]] = {}
        for ip, number in rows:
            if excluded and ip_excluded(ip, excluded):
                continue
            by_ip.setdefault(ip, [])
            if number not in by_ip[ip]:
                by_ip[ip].append(number)
        targets: list[str] = []
        for ip in list(by_ip)[: cfg.max_addresses]:
            ports = sorted(by_ip[ip], key=lambda p: (p not in DEFAULT_WEB_PORTS, p))[
                : cfg.max_ports_per_address
            ]
            targets.extend(f"{ip}:{port}" for port in ports)
        return targets

    def _persist(self, records) -> int:
        now = utc_now()
        known = set(
            self.session.execute(
                select(HttpAsset.url).where(HttpAsset.scan_id == self.ctx.scan_id)
            ).scalars()
        )
        answered = 0
        for record in records:
            fields = parse_httpx_record(record)
            url = fields.get("url")
            if not url or url in known:
                continue
            known.add(url)
            data = {k: v for k, v in fields.items() if k in _HTTP_FIELDS}
            self.session.add(
                HttpAsset(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    discovered_at=now,
                    **data,
                )
            )
            answered += 1
            if answered % 200 == 0:
                self.session.flush()
                self._check_abort()
        self.session.commit()
        return answered
