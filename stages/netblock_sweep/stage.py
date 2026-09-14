from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field

from sqlalchemy import select, text

from shared.definitions.intensity import TransportTool
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.enums.subdomain import SubdomainSource
from shared.logging import get_logger
from shared.models.subdomain import Subdomain
from shared.services.ip_asn import ranges_ready
from shared.services.ip_inventory import collect_ips
from shared.services.scope_filter import ip_excluded, matches_any
from shared.utils.datetime import utc_now
from stages.base import DOMAIN_TARGETS, Stage, StageResult
from stages.netblock_sweep.config import (
    MAX_ASN_ADDRESSES,
    MIN_ADDRESSES,
    MIN_SHARE,
    NetblockSweepConfig,
)
from stages.subdomain.parser import in_scope, normalize_host, passes_included
from tools.dnsx.client import DnsxClient, DnsxError
from tools.dnsx.parser import parse_dnsx_jsonl
from tools.ripestat.client import RIPEStatAPIError, RIPEStatClient

logger = get_logger(__name__)

_IPV4 = 4
_NAMED_FOREIGN = 5
_MIN_BUDGET = 120
_FLOOR_RATE = 20

_ASN_SQL = text("""
SELECT r.asn AS asn, r.as_name AS as_name, count(*) AS hosts
FROM unnest(CAST(:ips AS inet[])) AS ip
JOIN LATERAL (
    SELECT asn, as_name, end_ip FROM ip_asn_ranges
    WHERE start_ip <= ip ORDER BY start_ip DESC LIMIT 1
) r ON r.end_ip >= ip
GROUP BY r.asn, r.as_name
ORDER BY hosts DESC
""")


@dataclass
class Network:
    """One ASN the organisation appears to own, and the ranges it announces."""

    asn: int
    name: str
    hosts: int
    prefixes: list[str] = field(default_factory=list)
    addresses: int = 0


class NetblockSweepStage(Stage):
    name = "netblock_sweep"
    title = "Netblock Sweep"
    description = (
        "Find hosts by resolving reverse DNS across the network ranges "
        "the organisation announces."
    )
    phase = Phase.DISCOVERY.value
    depends_on = frozenset({"subdomain_discovery", "seed_resolution", "host_discovery"})
    group = StageGroup.HOSTS.value
    role = StageRole.CAPABILITY.value
    consumes = frozenset({AssetKind.ADDRESSES.value})
    produces = frozenset({AssetKind.HOSTS.value})
    applies_to = DOMAIN_TARGETS
    tools = ("dnsx",)
    transport_tool = TransportTool.DNSX.value
    thread_weight = 5 / 3
    touches_target = False
    config_model = NetblockSweepConfig

    def run(self) -> StageResult:
        self._check_abort()
        cfg = self.cfg

        if not ranges_ready(self.session):
            return StageResult(
                counts={"hosts": 0},
                warnings=["IP-to-ASN ranges are not loaded. No network attributed."],
                partial=True,
            )

        ips = collect_ips(self.session, self.ctx.scan_id)
        if not ips:
            return StageResult(counts={"hosts": 0})

        owned, rejected = self._owned_networks(ips)
        if not owned:
            note = (
                f"No network attributed. {rejected} candidate networks were too "
                "large or held too few addresses."
                if rejected
                else "No network attributed."
            )
            return StageResult(counts={"hosts": 0}, warnings=[note])

        addresses, truncated = self._sweep_list(owned, cfg)
        if not addresses:
            return StageResult(counts={"hosts": 0})

        label = ", ".join(f"AS{n.asn}" for n in owned)
        self.emit_progress(f"sweeping {len(addresses):,} addresses in {label}")

        names, note = self._sweep(addresses)
        in_scope_names, foreign = self._scope(names)
        added = self._persist(in_scope_names)

        warnings = [w for w in (note,) if w]
        if truncated:
            announced = sum(n.addresses for n in owned)
            warnings.append(
                f"{announced:,} addresses announced, {len(addresses):,} swept "
                "within the budget."
            )
        if foreign:
            warnings.append(
                f"{len(foreign)} hostnames in these ranges are outside the target "
                f"and were not stored: {', '.join(sorted(foreign)[:_NAMED_FOREIGN])}"
                + (
                    f" and {len(foreign) - _NAMED_FOREIGN} more"
                    if len(foreign) > _NAMED_FOREIGN
                    else ""
                )
            )

        self.emit_progress(
            f"netblock sweep found {added} hosts in {len(addresses):,} addresses"
        )
        return StageResult(
            counts={"hosts": added},
            warnings=warnings,
            partial=bool(note) or truncated,
        )

    def _owned_networks(self, ips: list[str]) -> tuple[list[Network], int]:
        """ASNs meeting the share and size thresholds."""
        rows = self.session.execute(_ASN_SQL, {"ips": ips}).all()
        client = RIPEStatClient(proxy_url=self.ctx.resolved.proxy_url)
        owned: list[Network] = []
        rejected = 0
        for asn, as_name, hosts in rows:
            if hosts < MIN_ADDRESSES or hosts * 100 < len(ips) * MIN_SHARE:
                continue
            self._check_abort()
            net = Network(asn=int(asn), name=as_name or "", hosts=int(hosts))
            try:
                data = client.announced_prefixes_sync(f"AS{net.asn}")
            except (RIPEStatAPIError, OSError) as exc:
                logger.warning("announced prefixes failed", asn=net.asn, error=str(exc))
                rejected += 1
                continue
            for entry in data.get("prefixes") or []:
                try:
                    block = ipaddress.ip_network(entry.get("prefix", ""), strict=False)
                except ValueError:
                    continue
                if block.version != _IPV4:
                    continue
                net.prefixes.append(str(block))
                net.addresses += block.num_addresses
            if not net.prefixes or net.addresses > MAX_ASN_ADDRESSES:
                rejected += 1
                continue
            owned.append(net)
        owned.sort(key=lambda n: (-n.hosts, n.addresses))
        return owned, rejected

    def _sweep_list(
        self, owned: list[Network], cfg: NetblockSweepConfig
    ) -> tuple[list[str], bool]:
        excluded = self.ctx.resolved.excluded_ips or []
        out: list[str] = []
        seen: set[str] = set()
        for net in owned:
            for prefix in net.prefixes:
                for addr in ipaddress.ip_network(prefix).hosts():
                    value = str(addr)
                    if value in seen or ip_excluded(value, excluded):
                        continue
                    seen.add(value)
                    out.append(value)
                    if len(out) >= cfg.max_sweep:
                        return out, True
        return out, False

    def _client(self, count: int) -> DnsxClient | None:
        try:
            return DnsxClient(
                timeout=max(_MIN_BUDGET, count // _FLOOR_RATE),
                threads=self.transport.threads,
                query_timeout=self.transport.timeout,
                recorder=self.ctx.recorder,
                extra_args=self.ctx.resolved.tool_args("dnsx"),
            )
        except DnsxError:
            logger.warning("dnsx unavailable, skipping netblock sweep")
            return None

    def _sweep(self, addresses: list[str]) -> tuple[dict[str, str], str | None]:
        """PTR across the range, then forward-confirm each name resolves back into it."""
        client = self._client(len(addresses))
        if client is None:
            return {}, f"dnsx unavailable. {len(addresses):,} addresses were not swept."

        result = client.ptr(addresses)
        found: dict[str, str] = {}
        for rec in parse_dnsx_jsonl(result.json_records):
            for raw in rec.ptr:
                name = normalize_host(raw)
                if name and name not in found:
                    found[name] = rec.host

        note = None
        if not result.success:
            kind = "timed out" if result.timed_out else "failed"
            note = f"dnsx {kind}. {len(addresses):,} addresses were only partly swept."

        if found:
            confirmed = self._forward_confirm(list(found), set(addresses))
            found = {name: ip for name, ip in found.items() if name in confirmed}
        return found, note

    def _forward_confirm(self, names: list[str], swept: set[str]) -> set[str]:
        """Names whose forward record points back into the swept range."""
        client = self._client(len(names))
        if client is None:
            return set(names)
        result = client.query(names, record_types=["a"])
        confirmed: set[str] = set()
        for rec in parse_dnsx_jsonl(result.json_records):
            host = normalize_host(rec.host)
            if host and any(ip in swept for ip in rec.a):
                confirmed.add(host)
        return confirmed

    def _scope(self, names: dict[str, str]) -> tuple[dict[str, str], set[str]]:
        domain = (self.ctx.target_value or "").strip().lower()
        included = [
            normalize_host(x) or x.strip().lower()
            for x in (self.ctx.resolved.included_subdomains or [])
        ]
        kept: dict[str, str] = {}
        foreign: set[str] = set()
        for name, ip in names.items():
            if not in_scope(name, domain):
                foreign.add(name)
                continue
            if not passes_included(name, included):
                continue
            kept[name] = ip
        return kept, foreign

    def _persist(self, names: dict[str, str]) -> int:
        if not names:
            return 0
        existing = {
            row.name: row
            for row in self.session.execute(
                select(Subdomain).where(Subdomain.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        }
        source = SubdomainSource.NETBLOCK.value
        now = utc_now()
        added = 0
        excluded = self.ctx.resolved.excluded_subdomains or []
        for name, ip in sorted(names.items()):
            row = existing.get(name)
            if row is not None:
                if source not in (row.sources or []):
                    row.sources = sorted({*(row.sources or []), source})
                    self.session.add(row)
                continue
            self.session.add(
                Subdomain(
                    scan_id=self.ctx.scan_id,
                    target_id=self.ctx.target_id,
                    project_id=self.ctx.project_id,
                    name=name,
                    sources=[source],
                    resolved_ips=[ip],
                    is_active=True,
                    is_excluded=matches_any(name, excluded),
                    discovered_at=now,
                )
            )
            added += 1
        self.session.commit()
        return added
