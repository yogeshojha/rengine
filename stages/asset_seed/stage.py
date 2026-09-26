from __future__ import annotations

import ipaddress
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from shared.definitions.endpoints import EndpointSource, parse_url
from shared.definitions.ports import SCHEME_PORTS, PortSource
from shared.definitions.rescan import RESCAN_SOURCE, SeedKind
from shared.enums.ip import IpSource
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.services import endpoint_inventory, ip_inventory, port_inventory
from shared.services.endpoint_inventory import EndpointObservation
from shared.services.endpoint_noise import NoisePolicy
from shared.services.port_inventory import ServiceObservation
from shared.utils.datetime import utc_now
from stages.asset_seed.config import AssetSeedConfig
from stages.base import ALL_TARGETS, Stage, StageResult
from tools.dnsx.client import DnsxClient, DnsxError

logger = get_logger(__name__)


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


_RECORD_TYPES = ("a", "aaaa", "cname")
_RESOLVE_TIMEOUT = 300
_RESOLVE_IDLE = 30
_WRITE_BATCH = 1000


class AssetSeedStage(Stage):
    name = "asset_seed"
    title = "Seed Assets"
    description = "Start a run from stored assets and assets chosen in an earlier run."
    phase = Phase.DISCOVERY.value
    group = StageGroup.HOSTS.value
    role = StageRole.SUPPORT.value
    produces = frozenset({AssetKind.HOSTS.value, AssetKind.ADDRESSES.value})
    applies_to = ALL_TARGETS
    touches_target = False
    catalog_hidden = True
    tools = ("dnsx",)
    config_model = AssetSeedConfig

    def run(self) -> StageResult:
        self._check_abort()
        hosts, addresses, urls = self._seeds()
        if not hosts and not addresses:
            return StageResult(
                counts={},
                warnings=["No assets were seeded for this run."],
                partial=True,
            )

        self._cnames: dict[str, str] = {}
        self._recovered = 0
        carried = self._carried(hosts)
        answers, unanswered = self._resolve([h for h in hosts if h not in carried])
        stored = self._persist_hosts(hosts, carried, answers)
        answered = [ip for answer in answers.values() for ip in answer.get("ips") or []]
        addresses = list(
            dict.fromkeys(
                addresses + [ip for ips in carried.values() for ip in ips] + answered
            )
        )
        materialized = ip_inventory.materialize(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            ips=addresses,
            source=IpSource.SEED.value,
        )
        seeded_urls = self._persist_urls(urls)
        self._persist_ports(answers, carried)
        self.session.commit()
        self.emit_progress(
            f"seeded {stored} hosts, {materialized} addresses and {seeded_urls} URLs"
        )
        counts = {"subdomains": stored, "ips": materialized}
        if seeded_urls:
            counts["endpoints"] = seeded_urls
        warnings: list[str] = []
        if self._recovered:
            counts["recovered"] = self._recovered
            warnings.append(
                f"dnsx dropped {self._recovered} of {stored} seeded hosts on the "
                "first pass. A second pass answered for them."
            )
        if unanswered:
            counts["unresolved"] = unanswered
            warnings.append(
                f"{unanswered} of {stored} seeded hosts have no DNS answer. "
                "They are stored and not probed."
            )
        return StageResult(counts=counts, warnings=warnings, partial=bool(warnings))

    def _persist_ports(self, answers: dict[str, dict], carried: dict) -> int:
        """Port rows for URL seeds on non-default ports."""
        if not self._url_ports:
            return 0
        observations: list[ServiceObservation] = []
        for host, ports in self._url_ports.items():
            ips = (
                [host]
                if _is_ip(host)
                else list(
                    (answers.get(host) or {}).get("ips") or carried.get(host) or []
                )
            )
            for ip in ips:
                for port, tls in sorted(ports):
                    observations.append(
                        ServiceObservation(
                            ip=ip,
                            port=port,
                            tls=tls,
                            is_http=True,
                            service_name="https" if tls else "http",
                        )
                    )
        if not observations:
            return 0
        return port_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            source=PortSource.SEED.value,
            observations=observations,
            keep_source=True,
        )

    def _persist_urls(self, urls: list[str]) -> int:
        """A URL seed carries the exact request shape a person chose, not just its host."""
        if not urls:
            return 0
        result = endpoint_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            source=EndpointSource.PROXY.value,
            observations=[EndpointObservation(url=url) for url in urls],
            policy=NoisePolicy.protected(),
        )
        return result.created + result.updated

    def _seeds(self) -> tuple[list[str], list[str], list[str]]:
        hosts: list[str] = []
        addresses: list[str] = []
        urls: list[str] = []
        self._sources: dict[str, str] = {}
        self._url_ports: dict[str, set[tuple[int, bool]]] = {}
        for seed in self.ctx.resolved.seed_assets or []:
            value = (seed.get("value") or "").strip()
            if not value:
                continue
            source = seed.get("source") or RESCAN_SOURCE
            if seed.get("kind") == SeedKind.ADDRESS.value:
                try:
                    ipaddress.ip_address(value)
                except ValueError:
                    logger.warning("invalid address seed: %s", value)
                    continue
                addresses.append(value)
            elif seed.get("kind") == SeedKind.URL.value:
                parsed = parse_url(value)
                if parsed is None:
                    logger.warning("invalid url seed: %s", value)
                    continue
                urls.append(parsed.url)
                if parsed.port != SCHEME_PORTS.get(parsed.scheme):
                    self._url_ports.setdefault(parsed.host, set()).add(
                        (parsed.port, parsed.scheme == "https")
                    )
                if _is_ip(parsed.host):
                    addresses.append(parsed.host)
                    continue
                hosts.append(parsed.host)
                self._sources[parsed.host] = source
            else:
                hosts.append(value.lower())
                self._sources[value.lower()] = source
        return (
            list(dict.fromkeys(hosts)),
            list(dict.fromkeys(addresses)),
            list(dict.fromkeys(urls)),
        )

    def _carried(self, hosts: list[str]) -> dict[str, list[str]]:
        """Resolved addresses the parent run already knew."""
        if not hosts:
            return {}
        parent = self.session.execute(
            select(Scan.parent_scan_id).where(Scan.id == self.ctx.scan_id)
        ).scalar_one_or_none()
        if parent is None:
            return {}
        rows = self.session.execute(
            select(Subdomain.name, Subdomain.resolved_ips, Subdomain.cname).where(
                Subdomain.scan_id == parent, Subdomain.name.in_(hosts)
            )
        ).all()
        self._cnames = {name: cname for name, _, cname in rows if cname}
        return {name: list(ips or []) for name, ips, _ in rows}

    def _resolve(self, hosts: list[str]) -> tuple[dict[str, dict], int]:
        """Two dnsx passes: the resolver answers nothing both for an absent name and a dropped query."""
        if not hosts:
            return {}, 0
        answers, failed = self._query(hosts)
        missing = [host for host in hosts if host not in answers]
        if missing and not failed:
            recovered, failed = self._query(missing)
            answers.update(recovered)
            self._recovered = len(recovered)
            missing = [host for host in missing if host not in answers]
        return answers, len(missing)

    def _query(self, hosts: list[str]) -> tuple[dict[str, dict], bool]:
        """One pass. The bool says the resolver broke, not that a name is absent."""
        try:
            client = DnsxClient(
                timeout=_RESOLVE_TIMEOUT,
                **self.wiring("dnsx"),
            )
        except DnsxError:
            logger.warning("dnsx unavailable, seeding hosts without resolution")
            return {}, True
        answers: dict[str, dict] = {}
        try:
            with client.stream_query(
                hosts, record_types=list(_RECORD_TYPES), idle_timeout=_RESOLVE_IDLE
            ) as stream:
                for rec in stream.records:
                    name = (rec.get("host") or "").strip().lower().rstrip(".")
                    if not name:
                        continue
                    cnames = rec.get("cname") or []
                    answers[name] = {
                        "ips": [
                            str(x)
                            for x in [*(rec.get("a") or []), *(rec.get("aaaa") or [])]
                        ],
                        "cname": str(cnames[0]) if cnames else None,
                    }
                    self._check_abort()
        except DnsxError as exc:
            logger.warning("dnsx seed resolution failed", error=str(exc))
            return answers, True
        return answers, False

    def _row(
        self, name: str, carried: dict[str, list[str]], answers: dict[str, dict]
    ) -> dict:
        answer = answers.get(name) or {}
        ips = carried.get(name) if name in carried else list(answer.get("ips") or [])
        cname = self._cnames.get(name) if name in carried else answer.get("cname")
        return {
            "resolved_ips": list(ips or []),
            "cname": cname,
            "is_active": name in carried or bool(ips) or bool(cname),
        }

    def _persist_hosts(
        self,
        hosts: list[str],
        carried: dict[str, list[str]],
        answers: dict[str, dict],
    ) -> int:
        """Insert in sorted key order."""
        if not hosts:
            return 0
        now = utc_now()
        rows = [
            {
                "id": uuid.uuid4(),
                "scan_id": self.ctx.scan_id,
                "target_id": self.ctx.target_id,
                "project_id": self.ctx.project_id,
                "name": name,
                "sources": [self._sources.get(name, RESCAN_SOURCE)],
                "tech": [],
                "interest_kinds": [],
                "discovered_at": now,
                "created_at": now,
                **self._row(name, carried, answers),
            }
            for name in sorted(hosts)
        ]
        for start in range(0, len(rows), _WRITE_BATCH):
            statement = insert(Subdomain).values(rows[start : start + _WRITE_BATCH])
            self.session.execute(
                statement.on_conflict_do_update(
                    constraint="uq_subdomain_scan_name",
                    set_={
                        "resolved_ips": statement.excluded.resolved_ips,
                        "cname": statement.excluded.cname,
                        "is_active": statement.excluded.is_active,
                    },
                    where=statement.excluded.is_active,
                )
            )
        return len(rows)
