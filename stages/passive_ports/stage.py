from __future__ import annotations

import ipaddress
import time

from sqlalchemy import select

from shared.definitions.ports import PortSource
from shared.definitions.surface import SurfaceDimension
from shared.enums.api_key import APIProvider
from shared.enums.scan import AssetKind, Phase, StageGroup, StageRole
from shared.logging import get_logger
from shared.models.ip_address import IpAddress
from shared.services import ip_inventory, port_inventory
from shared.services.api_key.sync_api_key import SyncAPIKeyService
from shared.services.port_inventory import ServiceObservation
from shared.services.scope_filter import ip_excluded
from stages.base import ALL_TARGETS, Stage, StageResult
from stages.passive_ports.config import (
    MAX_ADDRESSES,
    SHODAN_BUDGET_SECONDS,
    SHODAN_MAX_FAILURES,
    SHODAN_RETRY_SECONDS,
    PassivePortsConfig,
)
from tools.naabu.client import NaabuClient, NaabuError, NaabuOptions
from tools.shodan.client import (
    ShodanClient,
    ShodanError,
    ShodanRateLimitedError,
    ShodanRefusedError,
)
from tools.shodan.parser import parse_host

logger = get_logger(__name__)


class PassivePortsStage(Stage):
    name = "passive_ports"
    title = "Passive Port Discovery"
    description = "Read ports indexed for each address by internet-wide scanners."
    phase = Phase.EXPANSION.value
    depends_on = frozenset({"host_discovery", "seed_resolution", "subdomain_discovery"})
    group = StageGroup.SERVICES.value
    role = StageRole.SUPPORT.value
    consumes = frozenset({AssetKind.ADDRESSES.value})
    produces = frozenset({AssetKind.PORTS.value})
    applies_to = ALL_TARGETS
    tools = ("naabu",)
    api_keys = (APIProvider.SHODAN.value,)
    touches_target = False
    config_model = PassivePortsConfig

    def run(self) -> StageResult:
        self._check_abort()
        ip_inventory.ensure(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
        )
        self.publish_results(SurfaceDimension.IPS.value)
        addresses = self._candidates(MAX_ADDRESSES)
        if not addresses:
            return StageResult(counts={"known_ports": 0, "addresses": 0})

        warnings: list[str] = []
        found, failure = self._internetdb(addresses)
        if failure:
            warnings.append(failure)
        self._check_abort()
        self._write(PortSource.INTERNETDB, found)
        known = {(o.ip, o.port) for o in found}
        counts: dict[str, int] = {"addresses": len(addresses)}

        key = SyncAPIKeyService(self.session).get_key_for_provider(APIProvider.SHODAN)
        self.session.commit()
        if key:
            queue = self._shodan_queue(
                addresses, found, internetdb_failed=bool(failure)
            )
            looked, services, note = self._shodan(key, queue)
            self._write(PortSource.SHODAN, services)
            known |= {(o.ip, o.port) for o in services}
            counts["looked_up"] = looked
            counts["described"] = sum(1 for o in services if o.product or o.banner)
            if note:
                warnings.append(note)
            self.emit_progress(
                f"Shodan reported {len(services)} services on {looked} addresses"
            )

        counts["known_ports"] = len(known)
        self.emit_progress(
            f"{len(known)} ports indexed across {len(addresses)} addresses"
        )
        return StageResult(counts=counts, warnings=warnings, partial=bool(warnings))

    def _internetdb(
        self, addresses: list[str]
    ) -> tuple[list[ServiceObservation], str | None]:
        try:
            client = NaabuClient(
                options=NaabuOptions(
                    proxy_url=self.net_options().proxy_url,
                    extra_args=self.ctx.resolved.tool_args("naabu"),
                ),
                recorder=self.ctx.recorder,
            )
        except NaabuError as exc:
            logger.warning("naabu unavailable, skipping passive port lookup")
            return [], str(exc)
        try:
            found = client.passive(addresses)
        except NaabuError as exc:
            logger.warning("passive port lookup failed: %s", exc)
            note = f"Indexed ports not read. {exc}"
            self.emit_progress(note)
            return [], note
        return [
            ServiceObservation(
                ip=item["ip"],
                port=item["port"],
                protocol=item["protocol"],
                tls=item["tls"],
            )
            for item in found
        ], None

    def _write(self, source: PortSource, observations: list[ServiceObservation]) -> int:
        return port_inventory.upsert(
            self.session,
            scan_id=self.ctx.scan_id,
            target_id=self.ctx.target_id,
            project_id=self.ctx.project_id,
            source=source.value,
            observations=observations,
        )

    @staticmethod
    def _shodan_queue(
        addresses: list[str],
        found: list[ServiceObservation],
        *,
        internetdb_failed: bool,
    ) -> list[str]:
        """Addresses InternetDB indexed, most ports first, or every address when it failed."""
        if internetdb_failed:
            return addresses
        ports: dict[str, int] = {}
        for obs in found:
            ports[obs.ip] = ports.get(obs.ip, 0) + 1
        order = {ip: i for i, ip in enumerate(addresses)}
        return sorted(
            (ip for ip in addresses if ip in ports),
            key=lambda ip: (-ports[ip], order[ip]),
        )

    def _shodan(
        self, key: str, queue: list[str]
    ) -> tuple[int, list[ServiceObservation], str | None]:
        """Addresses looked up, the services Shodan reported, and why the pass stopped short."""
        services: list[ServiceObservation] = []
        looked = 0
        failures = 0
        deadline = time.monotonic() + SHODAN_BUDGET_SECONDS
        with ShodanClient(key) as client:
            for ip in queue:
                self._check_abort()
                if time.monotonic() >= deadline:
                    return (
                        looked,
                        services,
                        (
                            f"Shodan lookups stopped at the {SHODAN_BUDGET_SECONDS // 60}-minute "
                            f"budget: {looked:,} of {len(queue):,} addresses looked up."
                        ),
                    )
                try:
                    payload = self._lookup(client, ip)
                except ShodanRefusedError as exc:
                    return looked, services, f"{exc} Indexed banners not read."
                except ShodanError as exc:
                    failures += 1
                    if failures >= SHODAN_MAX_FAILURES:
                        return (
                            looked,
                            services,
                            (
                                f"Shodan lookups stopped after {failures} failed requests. {exc}"
                            ),
                        )
                    continue
                failures = 0
                looked += 1
                services.extend(
                    ServiceObservation(
                        ip=ip,
                        port=svc.port,
                        tls=svc.tls,
                        product=svc.product,
                        version=svc.version,
                        banner=svc.banner,
                        cpe=svc.cpe,
                    )
                    for svc in parse_host(payload)
                )
        return looked, services, None

    @staticmethod
    def _lookup(client: ShodanClient, ip: str) -> dict | None:
        try:
            return client.host(ip)
        except ShodanRateLimitedError:
            time.sleep(SHODAN_RETRY_SECONDS)
            return client.host(ip)

    def _candidates(self, budget: int) -> list[str]:
        excluded = self.ctx.resolved.excluded_ips or []
        rows = (
            self.session.execute(
                select(IpAddress.ip).where(IpAddress.scan_id == self.ctx.scan_id)
            )
            .scalars()
            .all()
        )
        out: list[str] = []
        for ip in dict.fromkeys(rows):
            try:
                if not ipaddress.ip_address(ip).is_global:
                    continue
            except ValueError:
                continue
            if excluded and ip_excluded(ip, excluded):
                continue
            out.append(ip)
            if len(out) >= budget:
                break
        return out
