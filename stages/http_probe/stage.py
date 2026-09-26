from __future__ import annotations

import random
from collections.abc import Iterable

from sqlalchemy import bindparam, delete, select, update
from sqlalchemy.orm import defer

from shared.definitions.intensity import TransportTool
from shared.definitions.ports import (
    DEFAULT_WEB_PORTS,
    PortSource,
    ServiceClass,
    service_class,
)
from shared.definitions.surface import SurfaceDimension
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.services import port_inventory, web_hygiene
from shared.services.port_inventory import ServiceObservation
from shared.utils.datetime import utc_now
from shared.utils.net import host_port
from shared.utils.software import parse_banner
from stages.base import Stage, StageResult
from stages.http_probe.config import (
    FOLLOW_REDIRECTS,
    MAX_PORTS_PER_HOST,
    HttpProbeConfig,
)
from tools.httpx.client import HttpxClient, HttpxError
from tools.httpx.parser import parse_httpx_record

logger = get_logger(__name__)

_IP_FAMILY = {TargetType.IP.value, TargetType.IP_RANGE.value, TargetType.ASN.value}
_MAX_TARGETS = 50000
_SHUFFLE_SEED = 1
_PROBE_CHUNK = 500
_WEB_CAPABLE = (ServiceClass.WEB.value, ServiceClass.OTHER.value)
_PERSIST_BATCH = 500
_PERSIST_SECONDS = 2.0

_HTTP_FIELDS = set(HttpAsset.model_fields)

_DENORM_FIELDS: dict[str, str] = {
    "http_url": "url",
    "final_url": "final_url",
    "http_status": "status_code",
    "page_title": "title",
    "content_type": "content_type",
    "content_length": "content_length",
    "response_time": "response_time",
    "webserver": "webserver",
    "tech": "tech",
    "is_cdn": "is_cdn",
    "cdn_name": "cdn_name",
    "waf": "waf",
    "asn": "asn",
    "asn_org": "asn_org",
    "favicon_hash": "favicon_hash",
    "tls_not_after": "tls_not_after",
    "tls_expired": "tls_expired",
    "tls_self_signed": "tls_self_signed",
}


_DENORM_UPDATE = (
    update(Subdomain)
    .where(
        Subdomain.scan_id == bindparam("b_scan"),
        Subdomain.name == bindparam("b_name"),
    )
    .values({column: bindparam(column) for column in _DENORM_FIELDS})
)


def _rank_of(scheme: str | None, status: int | None, port: int | None) -> tuple:
    alive = status is not None and 200 <= status < 400  # noqa: PLR2004
    return (scheme == "https", alive, port in (443, 80), -(port or 0))


def _rank(asset: HttpAsset) -> tuple:
    return _rank_of(asset.scheme, asset.status_code, asset.port)


class HttpProbeStage(Stage):
    name = "http_probe"
    title = "HTTP Probe"
    description = (
        "Fingerprint every host and port for live HTTP, technologies and titles."
    )
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"port_scan", "vhost"})
    group = StageGroup.WEB.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.HOSTS.value, AssetKind.ADDRESSES.value})
    produces = frozenset({AssetKind.HTTP_ASSETS.value})
    tools = ("httpx",)
    transport_tool = TransportTool.HTTPX.value
    config_model = HttpProbeConfig

    def run(self) -> StageResult:
        self._check_abort()
        net = self.net_options()
        targets = self._build_targets()
        if not targets:
            return StageResult(counts={"http_assets": 0})

        try:
            client = HttpxClient(
                rate_limit=self.transport.rate,
                threads=self.transport.threads,
                timeout=self.transport.timeout,
                proxy_url=net.proxy_url,
                headers=net.headers,
                probe_scheme=net.probe_scheme,
                follow_redirects=self.follow_redirects(FOLLOW_REDIRECTS),
                **self.wiring("httpx"),
            )
        except HttpxError as exc:
            logger.warning("httpx unavailable, skipping HTTP probe")
            return StageResult(warnings=[str(exc)], partial=True)

        stalled = [False]

        def _chunked() -> Iterable[dict]:
            for start in range(0, len(targets), _PROBE_CHUNK):
                self._check_abort()
                chunk = targets[start : start + _PROBE_CHUNK]
                with client.stream_probe(chunk) as stream:
                    yield from stream.records
                    stalled[0] = stalled[0] or stream.timed_out

        count, rejected = self._persist(_chunked())
        services = self._record_services()
        if self.ctx.target_type == TargetType.DOMAIN.value:
            self._denormalize_to_subdomains()
        web_hygiene.fold_onto_hosts(self.session, self.ctx.scan_id)
        self.session.commit()
        self.emit_progress(
            f"probed {len(targets)} host and port pairs, {count} answered HTTP"
        )
        warnings = []
        if stalled[0]:
            warnings.append(
                f"httpx stalled and was stopped. {len(targets):,} host and port "
                f"pairs were queued, {count:,} answered."
            )
        if rejected:
            warnings.append(f"{rejected:,} responses could not be stored")
        return StageResult(
            counts={"http_assets": count, "web_services": services},
            warnings=warnings,
            partial=bool(warnings),
        )

    def _port_map(self) -> dict[str, set[int]]:
        """Open ports per address, filtered to what can plausibly answer HTTP."""
        rows = self.session.execute(
            select(Port.ip, Port.number, Port.service_name, Port.service_class).where(
                Port.scan_id == self.ctx.scan_id
            )
        ).all()
        out: dict[str, set[int]] = {}
        for ip, number, name, klass in rows:
            if not self.cfg.probe_all_ports:
                resolved = klass or service_class(name, number)
                if resolved not in _WEB_CAPABLE:
                    continue
            out.setdefault(ip, set()).add(number)
        return out

    def _ports_for(self, ips: list[str], port_map: dict[str, set[int]]) -> list[int]:
        ports = set(DEFAULT_WEB_PORTS)
        for ip in ips or []:
            ports |= port_map.get(ip, set())
        ordered = sorted(ports, key=lambda p: (p not in DEFAULT_WEB_PORTS, p))
        return ordered[:MAX_PORTS_PER_HOST]

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
                targets.extend(
                    host_port(name, port)
                    for port in self._ports_for(resolved_ips or [], port_map)
                )
        elif target_type in _IP_FAMILY:
            ips = (
                self.session.execute(
                    select(IpAddress.ip).where(IpAddress.scan_id == self.ctx.scan_id)
                )
                .scalars()
                .all()
            )
            for ip in dict.fromkeys(ips):
                targets.extend(
                    host_port(ip, port) for port in self._ports_for([ip], port_map)
                )
        unique = list(dict.fromkeys(targets))
        random.Random(_SHUFFLE_SEED).shuffle(unique)  # noqa: S311
        return unique[:_MAX_TARGETS]

    def _record_services(self) -> int:
        """Fold every live HTTP response back onto its port."""
        resolved = self._resolved_ips()
        rows = self.session.execute(
            select(
                HttpAsset.host,
                HttpAsset.ip,
                HttpAsset.port,
                HttpAsset.scheme,
                HttpAsset.webserver,
            ).where(
                HttpAsset.scan_id == self.ctx.scan_id,
                HttpAsset.port > 0,
            )
        ).all()
        merged: dict[tuple[str, int], ServiceObservation] = {}
        for host, ip, port, scheme, webserver in rows:
            product, version, _distro = parse_banner(webserver)
            https = scheme == "https"
            addresses = set(resolved.get(host, ()))
            if ip:
                addresses.add(ip)
            for address in addresses:
                key = (address, port)
                current = merged.get(key)
                if current is not None and not https:
                    continue
                merged[key] = ServiceObservation(
                    ip=address,
                    port=port,
                    is_http=True,
                    tls=https,
                    service_name="https" if https else "http",
                    product=product,
                    version=version,
                )
        return port_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            source=PortSource.HTTP_PROBE.value,
            observations=list(merged.values()),
        )

    def _resolved_ips(self) -> dict[str, list[str]]:
        rows = self.session.execute(
            select(Subdomain.name, Subdomain.resolved_ips).where(
                Subdomain.scan_id == self.ctx.scan_id
            )
        ).all()
        return {name: list(ips or []) for name, ips in rows}

    def _persist(self, records: Iterable[dict]) -> tuple[int, int]:
        """Store every answer as it lands."""
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
        rejected = 0
        cleared = False
        best: dict[str, tuple] = {}
        summaries: dict[str, dict] = {}

        def _write(batch: list[HttpAsset]) -> int:
            nonlocal rejected, cleared
            if not cleared:
                self.session.execute(
                    delete(HttpAsset).where(HttpAsset.scan_id == self.ctx.scan_id)
                )
                cleared = True
            bad = self.flush_rows(batch)
            rejected += bad
            self._denormalize_batch(summaries)
            summaries.clear()
            self.session.commit()
            return len(batch) - bad

        sink = self.results_sink(
            SurfaceDimension.WEB_ASSETS.value,
            _write,
            rows=_PERSIST_BATCH,
            seconds=_PERSIST_SECONDS,
        )
        for record in records:
            fields = parse_httpx_record(record)
            url = fields.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            if fields.get("asn") is None and fields.get("ip") in ip_asn:
                fields["asn"], fields["asn_org"] = ip_asn[fields["ip"]]
            data = {k: v for k, v in fields.items() if k in _HTTP_FIELDS}
            self._note_summary(data, best, summaries)
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
        if not cleared:
            self.session.execute(
                delete(HttpAsset).where(HttpAsset.scan_id == self.ctx.scan_id)
            )
            self.session.commit()
        return len(seen) - rejected, rejected

    @staticmethod
    def _note_summary(
        data: dict, best: dict[str, tuple], summaries: dict[str, dict]
    ) -> None:
        """Keep the strongest answer per host."""
        host = data.get("host")
        if not host:
            return
        rank = _rank_of(data.get("scheme"), data.get("status_code"), data.get("port"))
        if host in best and rank <= best[host]:
            return
        best[host] = rank
        summaries[host] = {
            column: (
                list(data.get(field) or []) if column == "tech" else data.get(field)
            )
            for column, field in _DENORM_FIELDS.items()
        }

    def _denormalize_batch(self, summaries: dict[str, dict]) -> None:
        if not summaries or self.ctx.target_type != TargetType.DOMAIN.value:
            return
        self.session.connection().execute(
            _DENORM_UPDATE,
            [
                {"b_scan": self.ctx.scan_id, "b_name": host, **values}
                for host, values in summaries.items()
            ],
        )

    def _denormalize_to_subdomains(self) -> None:
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
            for column, field in _DENORM_FIELDS.items():
                value = getattr(asset, field)
                setattr(sub, column, list(value or []) if column == "tech" else value)
            self.session.add(sub)
        self.session.commit()
