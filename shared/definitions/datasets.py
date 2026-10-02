"""Datasets the instance downloads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.bounty_programs import ProgramSource
from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS
from shared.definitions.threat_intel import (
    FEEDS_BY_KIND,
    STALE_AFTER_HOURS,
    FeedKind,
)
from shared.definitions.vulnerabilities import TemplateOrigin


class DatasetKind(StrEnum):
    LIBRARY = "library"
    EPSS = FeedKind.EPSS.value
    KEV = FeedKind.KEV.value
    NVD = FeedKind.NVD.value
    IP_RANGES = "ip_ranges"
    PROGRAM_FEED = "program_feed"
    AI_PRICES = "ai_prices"


IP_RANGES_STALE_AFTER_HOURS = 14 * 24


@dataclass(frozen=True)
class DatasetSpec:
    kind: str
    label: str
    description: str
    rows_noun: str
    table: str
    task: str
    where: str = ""
    task_kwargs: tuple[tuple[str, object], ...] = ()
    stale_after_hours: int | None = STALE_AFTER_HOURS
    capability: str | None = None
    # follows instance_settings.threat_intel_auto_sync
    auto_sync: bool = False


def _feed(kind: FeedKind) -> DatasetSpec:
    spec = FEEDS_BY_KIND[kind.value]
    return DatasetSpec(
        kind=spec.kind,
        label=spec.label,
        description=spec.tagline,
        rows_noun=spec.rows_noun,
        table=spec.rows_table,
        task="app.tasks.threat_intel.refresh",
        task_kwargs=(("feeds", (spec.kind,)), ("force", True)),
        auto_sync=True,
    )


DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        kind=DatasetKind.LIBRARY.value,
        label="Check library",
        description="Nuclei templates the vulnerability scan selects from",
        rows_noun="checks",
        table="vuln_templates",
        where=f"origin = '{TemplateOrigin.OFFICIAL.value}'",
        task="app.tasks.vuln_templates.sync",
    ),
    _feed(FeedKind.EPSS),
    _feed(FeedKind.KEV),
    _feed(FeedKind.NVD),
    DatasetSpec(
        kind=DatasetKind.IP_RANGES.value,
        label="IP ranges",
        description="ASN and country per address",
        rows_noun="ranges",
        table="ip_asn_ranges",
        task="app.tasks.ip_asn.refresh",
        stale_after_hours=IP_RANGES_STALE_AFTER_HOURS,
    ),
    DatasetSpec(
        kind=DatasetKind.PROGRAM_FEED.value,
        label="Program feed",
        description="Public bug bounty programs and their scope",
        rows_noun="programs",
        table="bounty_programs",
        where=f"source = '{ProgramSource.FEED.value}'",
        task="app.tasks.bounty_programs.sync_feed",
        stale_after_hours=None,
        capability=CAP_BOUNTY_PROGRAMS,
    ),
    DatasetSpec(
        kind=DatasetKind.AI_PRICES.value,
        label="Model prices",
        description="List prices per AI model, from OpenRouter",
        rows_noun="models",
        table="ai_prices",
        task="app.tasks.daily.run",
        task_kwargs=(("jobs", (DatasetKind.AI_PRICES.value,)),),
    ),
)

DATASETS_BY_KIND: dict[str, DatasetSpec] = {spec.kind: spec for spec in DATASETS}
