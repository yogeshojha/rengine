from __future__ import annotations

from sqlalchemy import delete, select

from engines.base import Engine, EngineResult
from engines.http_probe.config import HttpProbeConfig
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.utils.datetime import utc_now
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)

_IP_FAMILY = {TargetType.IP.value, TargetType.IP_RANGE.value, TargetType.ASN.value}
_DEFAULT_PORTS = (80, 443)
_MAX_TARGETS = 50000


class HttpProbeEngine(Engine):
    name = "http_probe"

    def should_run(self) -> bool:
        return HttpProbeConfig.from_resolved(self.ctx.resolved).enabled

    def run(self) -> EngineResult:
        self._check_abort()
        cfg = HttpProbeConfig.from_resolved(self.ctx.resolved)
        net = self.net_options()
        targets = self._build_targets()
        if not targets:
            return EngineResult(counts={"http_assets": 0})

        try:
            client = HttpxClient(
                rate_limit=cfg.rate_limit,
                threads=cfg.threads,
                timeout=cfg.timeout,
                proxy_url=net.proxy_url,
                headers=net.headers,
                follow_redirects=cfg.follow_redirects,
                screenshot=False,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("httpx"),
            )
        except HttpxError:
            logger.warning("httpx unavailable, skipping HTTP probe")
            return EngineResult(counts={"http_assets": 0})

        records = client.probe(targets)
        self._check_abort()
        count = self._persist(records)
        self.emit_progress(
            f"probed {len(targets)} targets → {count} live HTTP services"
        )
        return EngineResult(counts={"http_assets": count})

    def _port_map(self) -> dict[str, set[int]]:
        rows = self.session.execute(
            select(Port.ip, Port.number).where(Port.scan_id == self.ctx.scan_id)
        ).all()
        out: dict[str, set[int]] = {}
        for ip, number in rows:
            out.setdefault(ip, set()).add(number)
        return out

    def _build_targets(self) -> list[str]:
        target_type = self.ctx.target_type
        if target_type == TargetType.URL.value:
            return [self.ctx.target_value.strip()]

        port_map = self._port_map()
        targets: list[str] = []
        if target_type == TargetType.DOMAIN.value:
            subs = (
                self.session.execute(
                    select(Subdomain).where(
                        Subdomain.scan_id == self.ctx.scan_id,
                        Subdomain.is_excluded.is_(False),
                    )
                )
                .scalars()
                .all()
            )
            for sub in subs:
                if sub.is_wildcard or not sub.is_active:
                    continue
                ports = set(_DEFAULT_PORTS)
                for ip in sub.resolved_ips or []:
                    ports |= port_map.get(ip, set())
                targets.extend(f"{sub.name}:{port}" for port in sorted(ports))
        elif target_type in _IP_FAMILY:
            ips = (
                self.session.execute(
                    select(IpAddress.ip).where(IpAddress.scan_id == self.ctx.scan_id)
                )
                .scalars()
                .all()
            )
            for ip in dict.fromkeys(ips):
                ports = set(_DEFAULT_PORTS) | port_map.get(ip, set())
                targets.extend(f"{ip}:{port}" for port in sorted(ports))
        return list(dict.fromkeys(targets))[:_MAX_TARGETS]

    def _persist(self, records: list[dict]) -> int:
        self.session.execute(
            delete(HttpAsset).where(HttpAsset.scan_id == self.ctx.scan_id)
        )
        now = utc_now()
        ip_asn = {
            row.ip: (row.asn, row.asn_org)
            for row in self.session.execute(
                select(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        }
        seen: set[str] = set()
        for record in records:
            fields = parse_httpx_record(record)
            url = fields["url"]
            if not url or url in seen:
                continue
            seen.add(url)
            asn, asn_org = fields["asn"], fields["asn_org"]
            if asn is None and fields["ip"] in ip_asn:
                asn, asn_org = ip_asn[fields["ip"]]
            self.session.add(
                HttpAsset(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    url=url[:2000],
                    host=(fields["host"] or "")[:500],
                    port=fields["port"],
                    scheme=fields["scheme"],
                    status_code=fields["status_code"],
                    title=fields["title"],
                    webserver=fields["webserver"],
                    content_length=fields["content_length"],
                    content_type=fields["content_type"],
                    location=fields["location"],
                    tech=fields["tech"],
                    ip=fields["ip"],
                    cname=fields["cname"],
                    asn=asn,
                    asn_org=asn_org,
                    is_cdn=fields["is_cdn"],
                    cdn_name=fields["cdn_name"],
                    jarm=fields["jarm"],
                    favicon_hash=fields["favicon_hash"],
                    content_hash=fields["content_hash"],
                    tls_issuer=fields["tls_issuer"],
                    tls_subject_cn=fields["tls_subject_cn"],
                    tls_sans=fields["tls_sans"],
                    tls_not_after=fields["tls_not_after"],
                    tls_self_signed=fields["tls_self_signed"],
                    tls_expired=fields["tls_expired"],
                    tls_version=fields["tls_version"],
                    screenshot_path=fields["screenshot_path"],
                    discovered_at=now,
                )
            )
        self.session.commit()
        return len(seen)
