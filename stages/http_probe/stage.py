from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import defer

from shared.enums.scan import Phase
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.utils.datetime import utc_now
from stages.base import Stage, StageResult
from stages.http_probe.config import HttpProbeConfig
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)

_IP_FAMILY = {TargetType.IP.value, TargetType.IP_RANGE.value, TargetType.ASN.value}
_DEFAULT_PORTS = (80, 443)
_MAX_TARGETS = 50000
_PERSIST_BATCH = 500

_HTTP_FIELDS = set(HttpAsset.model_fields)


def _rank(asset: HttpAsset) -> tuple:
    alive = asset.status_code is not None and 200 <= asset.status_code < 400  # noqa: PLR2004
    return (asset.scheme == "https", alive, asset.port in (443, 80), -(asset.port or 0))


class HttpProbeStage(Stage):
    name = "http_probe"
    title = "HTTP Probe"
    description = "Fingerprint every host/port for live HTTP, tech and titles."
    phase = Phase.EXPANSION.value
    level = 2
    tools = ("httpx",)
    config_model = HttpProbeConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        net = self.net_options()
        targets = self._build_targets()
        if not targets:
            return StageResult(counts={"http_assets": 0})

        try:
            client = HttpxClient(
                rate_limit=cfg.rate,
                threads=cfg.threads,
                timeout=cfg.timeout,
                proxy_url=net.proxy_url,
                headers=net.headers,
                follow_redirects=cfg.follow_redirects,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("httpx"),
            )
        except HttpxError:
            logger.warning("httpx unavailable, skipping HTTP probe")
            return StageResult(counts={"http_assets": 0})

        with client.stream_probe(targets) as records:
            self._check_abort()
            count = self._persist(records)
        if self.ctx.target_type == TargetType.DOMAIN.value:
            self._denormalize_to_subdomains()
        self.emit_progress(
            f"probed {len(targets)} targets → {count} live HTTP services"
        )
        return StageResult(counts={"http_assets": count})

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
            rows = self.session.execute(
                select(
                    Subdomain.name,
                    Subdomain.is_wildcard,
                    Subdomain.is_active,
                    Subdomain.resolved_ips,
                ).where(
                    Subdomain.scan_id == self.ctx.scan_id,
                    Subdomain.is_excluded.is_(False),
                )
            ).all()
            for name, is_wildcard, is_active, resolved_ips in rows:
                if is_wildcard or not is_active:
                    continue
                ports = set(_DEFAULT_PORTS)
                for ip in resolved_ips or []:
                    ports |= port_map.get(ip, set())
                targets.extend(f"{name}:{port}" for port in sorted(ports))
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

    def _persist(self, records: Iterable[dict]) -> int:
        self.session.execute(
            delete(HttpAsset).where(HttpAsset.scan_id == self.ctx.scan_id)
        )
        now = utc_now()
        ip_asn = {
            ip: (asn, asn_org)
            for ip, asn, asn_org in self.session.execute(
                select(IpAddress.ip, IpAddress.asn, IpAddress.asn_org).where(
                    IpAddress.scan_id == self.ctx.scan_id
                )
            ).all()
        }
        seen: set[str] = set()
        batch: list[HttpAsset] = []

        def _flush() -> None:
            if not batch:
                return
            self.session.flush()
            for obj in batch:
                self.session.expunge(obj)  # free the row (incl. body) from RAM
            batch.clear()

        for record in records:
            fields = parse_httpx_record(record)
            url = fields.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            if fields.get("asn") is None and fields.get("ip") in ip_asn:
                fields["asn"], fields["asn_org"] = ip_asn[fields["ip"]]
            data = {k: v for k, v in fields.items() if k in _HTTP_FIELDS}
            asset = HttpAsset(
                scan_id=self.ctx.scan_id,
                target_id=self.ctx.target_id,
                project_id=self.ctx.project_id,
                discovered_at=now,
                **data,
            )
            self.session.add(asset)
            batch.append(asset)
            if len(batch) >= _PERSIST_BATCH:
                _flush()
                self._check_abort()
        _flush()
        self.session.commit()
        return len(seen)

    def _denormalize_to_subdomains(self) -> None:
        # defer heavy raw-capture columns — denormalize only reads small summary fields
        assets = (
            self.session.execute(
                select(HttpAsset)
                .where(HttpAsset.scan_id == self.ctx.scan_id)
                .options(
                    defer(HttpAsset.response_body),
                    defer(HttpAsset.raw_request),
                    defer(HttpAsset.raw_response_header),
                    defer(HttpAsset.response_headers),
                )
            )
            .scalars()
            .all()
        )
        primary: dict[str, HttpAsset] = {}
        for asset in assets:
            current = primary.get(asset.host)
            if current is None or _rank(asset) > _rank(current):
                primary[asset.host] = asset

        subs = (
            self.session.execute(
                select(Subdomain).where(Subdomain.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        for sub in subs:
            asset = primary.get(sub.name)
            if asset is None:
                continue
            sub.http_url = asset.url
            sub.final_url = asset.final_url
            sub.http_status = asset.status_code
            sub.page_title = asset.title
            sub.content_type = asset.content_type
            sub.content_length = asset.content_length
            sub.response_time = asset.response_time
            sub.webserver = asset.webserver
            sub.tech = list(asset.tech or [])
            sub.is_cdn = asset.is_cdn
            sub.cdn_name = asset.cdn_name
            sub.waf = asset.waf
            sub.asn = asset.asn
            sub.asn_org = asset.asn_org
            sub.favicon_hash = asset.favicon_hash
            sub.tls_not_after = asset.tls_not_after
            sub.tls_expired = asset.tls_expired
            sub.tls_self_signed = asset.tls_self_signed
            self.session.add(sub)
        self.session.commit()
