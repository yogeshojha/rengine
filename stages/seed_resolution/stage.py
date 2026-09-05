from __future__ import annotations

import ipaddress

from sqlalchemy import delete

from shared.enums.ip import IpSource
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from shared.utils.cidr import expand_network, parse_network
from shared.utils.datetime import utc_now
from stages.base import IP_TARGETS, Stage, StageResult
from stages.seed_resolution.config import SeedResolutionConfig
from tools.ripestat.service import RIPEStatError, RIPEStatService

logger = get_logger(__name__)

_MAX_ASN_PREFIXES = 256


def _parse_asn(value: str) -> int | None:
    try:
        return int(value.upper().replace("AS", "").strip())
    except ValueError:
        return None


class SeedResolutionStage(Stage):
    name = "seed_resolution"
    title = "Seed Resolution"
    description = "Expand an IP, netblock or ASN seed into individual hosts."
    phase = Phase.DISCOVERY.value
    group = StageGroup.ADDRESSES.value
    role = StageRole.SUPPORT.value
    produces = frozenset({AssetKind.ADDRESSES.value})
    applies_to = IP_TARGETS
    touches_target = False
    config_model = SeedResolutionConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg
        value = self.ctx.target_value.strip()

        if self.ctx.target_type == TargetType.IP.value:
            records, truncated = self._from_ip(value), False
        elif self.ctx.target_type == TargetType.IP_RANGE.value:
            records, truncated = self._from_cidr(value, cfg)
        else:
            records, truncated = self._from_asn(value, cfg)

        self._check_abort()
        count = self._persist(records)
        if truncated:
            self.emit_progress(
                f"large seed sampled to {count} hosts ({cfg.asn_scan_mode} mode)"
            )
        self.emit_progress(f"discovered {count} IP assets")
        return StageResult(counts={"ips": count})

    def _from_ip(self, value: str) -> list[dict]:
        try:
            addr = ipaddress.ip_address(value)
        except ValueError:
            logger.warning("invalid IP seed: %s", value)
            return []
        return [
            {
                "ip": str(addr),
                "version": addr.version,
                "source": IpSource.SEED.value,
                "prefix": None,
                "asn": None,
            }
        ]

    def _from_cidr(
        self, value: str, cfg: SeedResolutionConfig
    ) -> tuple[list[dict], bool]:
        net = parse_network(value)
        if net is None:
            logger.warning("invalid CIDR seed: %s", value)
            return [], False
        ips, truncated = expand_network(
            value,
            max_hosts=cfg.max_expansion_hosts,
            skip_private=cfg.cidr_skip_rfc1918,
        )
        prefix = str(net)
        records = [
            {
                "ip": ip,
                "version": net.version,
                "source": IpSource.CIDR_EXPANSION.value,
                "prefix": prefix,
                "asn": None,
            }
            for ip in ips
        ]
        return records, truncated

    def _from_asn(
        self, value: str, cfg: SeedResolutionConfig
    ) -> tuple[list[dict], bool]:
        prefixes = self._asn_prefixes(value)[:_MAX_ASN_PREFIXES]
        if not prefixes:
            logger.warning("no announced prefixes for %s", value)
            return [], False
        asn = _parse_asn(value)
        per_prefix = max(cfg.max_expansion_hosts // len(prefixes), 1)
        records: list[dict] = []
        truncated = False
        for prefix in prefixes:
            if len(records) >= cfg.max_expansion_hosts:
                truncated = True
                break
            net = parse_network(prefix)
            if net is None:
                continue
            ips, was_truncated = expand_network(
                prefix, max_hosts=per_prefix, skip_private=cfg.cidr_skip_rfc1918
            )
            truncated = truncated or was_truncated
            records.extend(
                {
                    "ip": ip,
                    "version": net.version,
                    "source": IpSource.ASN_EXPANSION.value,
                    "prefix": prefix,
                    "asn": asn,
                }
                for ip in ips
            )
        return records, truncated

    def _asn_prefixes(self, value: str) -> list[str]:
        svc = RIPEStatService()
        try:
            result = svc.announced_prefixes_sync(self.session, value, cached_only=True)
            if result is None:
                result = svc.announced_prefixes_sync(
                    self.session, value, cached_only=False
                )
        except RIPEStatError as exc:
            logger.warning("ASN prefix lookup failed for %s: %s", value, exc)
            return []
        if result is None:
            return []
        return [p.prefix for p in result.data if getattr(p, "prefix", None)]

    def _persist(self, records: list[dict]) -> int:
        self.session.execute(
            delete(IpAddress).where(IpAddress.scan_id == self.ctx.scan_id)
        )
        now = utc_now()
        seen: set[str] = set()
        for rec in records:
            ip = rec["ip"]
            if ip in seen:
                continue
            seen.add(ip)
            self.session.add(
                IpAddress(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    ip=ip,
                    version=rec["version"],
                    source=rec["source"],
                    prefix=rec.get("prefix"),
                    asn=rec.get("asn"),
                    discovered_at=now,
                )
            )
        self.session.commit()
        return len(seen)
