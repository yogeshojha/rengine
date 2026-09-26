from __future__ import annotations

import random

from sqlalchemy import select

from shared.definitions.intensity import TransportTool
from shared.definitions.ports import DEFAULT_WEB_PORTS, ServiceClass
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.services import vuln_inventory
from shared.services.origin_exposure import OriginExposureService
from shared.services.scope_filter import ip_excluded
from shared.utils.datetime import utc_now
from shared.utils.net import host_port
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.origin_probe.config import MAX_PORTS_PER_ADDRESS, OriginProbeConfig
from stages.origin_probe.finding import origin_finding
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)

_WRITE_BATCH = 200
_SHUFFLE_SEED = 1
_PROBE_CHUNK = 500

_HTTP_FIELDS = set(HttpAsset.model_fields)


class OriginProbeStage(Stage):
    name = "origin_probe"
    title = "Origin Probe"
    description = (
        "Request each address by IP and record what it serves without a hostname."
    )
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"http_probe"})
    group = StageGroup.SERVICES.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.PORTS.value})
    applies_to = ALL_TARGETS
    tools = ("httpx",)
    transport_tool = TransportTool.HTTPX.value
    thread_weight = 0.2
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
                rate_limit=self.transport.rate,
                threads=self.transport.threads,
                timeout=self.transport.timeout,
                proxy_url=net.proxy_url,
                headers=net.headers,
                probe_scheme=net.probe_scheme,
                follow_redirects=self.follow_redirects(False),
                **self.wiring("httpx"),
            )
        except HttpxError as exc:
            logger.warning("httpx unavailable, skipping origin probe")
            return StageResult(warnings=[str(exc)], partial=True)

        self.emit_progress(f"requesting {len(targets)} addresses without a hostname")
        stalled = [False]

        def _chunked():
            for start in range(0, len(targets), _PROBE_CHUNK):
                self._check_abort()
                chunk = targets[start : start + _PROBE_CHUNK]
                with client.stream_probe(chunk) as stream:
                    yield from stream.records
                    stalled[0] = stalled[0] or stream.timed_out

        answered, rejected = self._persist(_chunked())
        self.emit_progress(f"{answered} of {len(targets)} answered by address alone")
        exposed = self._record_exposure()
        warnings = []
        if stalled[0]:
            warnings.append(
                f"httpx stalled and was stopped. {len(targets):,} addresses queued."
            )
        if rejected:
            warnings.append(f"{rejected:,} responses could not be stored")
        return StageResult(
            counts={
                "probed": len(targets),
                "answered": answered,
                "vulnerabilities": exposed,
            },
            warnings=warnings,
            partial=bool(warnings),
        )

    def _record_exposure(self) -> int:
        """The correlation the read model already computes, written down as findings."""
        exposure = OriginExposureService(self.session).run(self.ctx.scan_id)
        findings = [origin_finding(found) for found in exposure.findings]
        stored = vuln_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            findings=findings,
        )
        self.session.commit()
        if stored:
            self.publish_results(SurfaceDimension.VULNERABILITIES.value)
            self.emit_progress(
                f"{stored} address{'' if stored == 1 else 'es'} answer the same "
                "application as a name behind the CDN"
            )
        return stored

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
                :MAX_PORTS_PER_ADDRESS
            ]
            targets.extend(host_port(ip, port) for port in ports)
        random.Random(_SHUFFLE_SEED).shuffle(targets)  # noqa: S311
        return targets

    def _persist(self, records) -> tuple[int, int]:
        now = utc_now()
        rejected = 0
        known = set(
            self.session.execute(
                select(HttpAsset.url).where(HttpAsset.scan_id == self.ctx.scan_id)
            ).scalars()
        )

        def _write(batch: list[HttpAsset]) -> int:
            nonlocal rejected
            bad = self.flush_rows(batch)
            rejected += bad
            self.session.commit()
            return len(batch) - bad

        sink = self.results_sink(
            SurfaceDimension.WEB_ASSETS.value, _write, rows=_WRITE_BATCH
        )
        for record in records:
            fields = parse_httpx_record(record)
            url = fields.get("url")
            if not url or url in known:
                continue
            known.add(url)
            data = {k: v for k, v in fields.items() if k in _HTTP_FIELDS}
            sink.add(
                HttpAsset(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    discovered_at=now,
                    **data,
                )
            )
            if sink.pending == 0:
                self._check_abort()
        sink.close()
        return sink.written, rejected
