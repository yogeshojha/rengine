"""Stages the orchestrator composes into the scan canvas (same level = parallel)."""

from __future__ import annotations

from dataclasses import dataclass, field

from engines.base import Engine
from engines.cdn_check import CdnCheckEngine
from engines.http_probe import HttpProbeEngine
from engines.ip_enrichment import IpEnrichmentEngine
from engines.port_scan import PortScanEngine
from engines.reverse_dns import ReverseDnsEngine
from engines.seed_resolution import SeedResolutionEngine
from engines.subdomain.engine import SubdomainEngine
from engines.target_enrichment import TargetEnrichmentEngine
from shared.enums.scan import PHASE_ORDER, Phase
from shared.enums.target import TargetType

_ALL_TYPES: frozenset[str] = frozenset(t.value for t in TargetType)
_IP_FAMILY: frozenset[str] = frozenset(
    {TargetType.IP.value, TargetType.IP_RANGE.value, TargetType.ASN.value}
)


@dataclass(frozen=True)
class StageSpec:
    name: str
    title: str
    phase: str
    level: int
    engine_cls: type[Engine]
    applies_to: frozenset[str] = field(default_factory=lambda: _ALL_TYPES)


STAGES: tuple[StageSpec, ...] = (
    StageSpec(
        name="target_enrichment",
        title="Target Enrichment",
        phase=Phase.DISCOVERY.value,
        level=0,
        engine_cls=TargetEnrichmentEngine,
        applies_to=_ALL_TYPES,
    ),
    StageSpec(
        name="seed_resolution",
        title="Seed Resolution",
        phase=Phase.DISCOVERY.value,
        level=0,
        engine_cls=SeedResolutionEngine,
        applies_to=_IP_FAMILY,
    ),
    StageSpec(
        name="reverse_dns",
        title="Reverse DNS",
        phase=Phase.DISCOVERY.value,
        level=1,
        engine_cls=ReverseDnsEngine,
        applies_to=_IP_FAMILY,
    ),
    StageSpec(
        name="ip_enrichment",
        title="IP Enrichment",
        phase=Phase.DISCOVERY.value,
        level=1,
        engine_cls=IpEnrichmentEngine,
        applies_to=_IP_FAMILY,
    ),
    StageSpec(
        name="subdomain_discovery",
        title="Subdomain Discovery",
        phase=Phase.EXPANSION.value,
        level=0,
        engine_cls=SubdomainEngine,
        applies_to=frozenset({TargetType.DOMAIN.value}),
    ),
    StageSpec(
        name="cdn_check",
        title="CDN / WAF Detection",
        phase=Phase.EXPANSION.value,
        level=1,
        engine_cls=CdnCheckEngine,
        applies_to=_IP_FAMILY,
    ),
    StageSpec(
        name="port_scan",
        title="Port Scan",
        phase=Phase.EXPANSION.value,
        level=1,
        engine_cls=PortScanEngine,
        applies_to=_ALL_TYPES,
    ),
    StageSpec(
        name="http_probe",
        title="HTTP Probe",
        phase=Phase.EXPANSION.value,
        level=2,
        engine_cls=HttpProbeEngine,
        applies_to=_ALL_TYPES,
    ),
)

STAGE_BY_NAME: dict[str, StageSpec] = {s.name: s for s in STAGES}


def ordered_levels() -> list[list[StageSpec]]:
    """Stages grouped by (phase, level), ascending — the canvas execution order."""
    groups: dict[tuple[int, int], list[StageSpec]] = {}
    for spec in STAGES:
        key = (PHASE_ORDER.get(spec.phase, 99), spec.level)
        groups.setdefault(key, []).append(spec)
    return [groups[key] for key in sorted(groups)]
