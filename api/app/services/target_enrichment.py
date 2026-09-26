"""The three enrichments a target can be queued for, described once."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.services.celery_dispatch import (
    dispatch_dns_lookups,
    dispatch_ripestat_enrichment,
    dispatch_whois_lookups,
)
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from collections.abc import Callable

    from shared.models.target import Target

BGP_ELIGIBLE_TYPES = frozenset({TargetType.IP, TargetType.IP_RANGE, TargetType.ASN})
DNS_ELIGIBLE_TYPES = frozenset({TargetType.DOMAIN, TargetType.URL})


class EnrichmentKind(StrEnum):
    WHOIS = "whois"
    DNS = "dns"
    BGP = "bgp"


@dataclass(frozen=True)
class Enrichment:
    kind: EnrichmentKind
    label: str
    # None: every target type
    eligible: frozenset[TargetType] | None
    eligible_label: str
    status_field: str
    # BGP keeps no error column: its summary row carries the failure
    error_field: str | None
    dispatch: Callable[[list[str]], object]

    def applies_to(self, target: Target) -> bool:
        return self.eligible is None or target.target_type in self.eligible

    def not_applicable(self, target: Target) -> str:
        return (
            f"{self.label} does not apply to {target.target_type.value} targets. "
            f"{self.eligible_label} targets only."
        )

    def mark_pending(self, target: Target) -> None:
        """Queue state on the row: pending, the last error cleared."""
        setattr(target, self.status_field, TaskStatus.PENDING)
        if self.error_field is not None:
            setattr(target, self.error_field, None)
        target.updated_at = utc_now()

    def queued(self, target: Target) -> str:
        return f"{self.label} queued for {target.target_value}"


ENRICHMENTS: dict[EnrichmentKind, Enrichment] = {
    EnrichmentKind.WHOIS: Enrichment(
        kind=EnrichmentKind.WHOIS,
        label="WHOIS lookup",
        eligible=None,
        eligible_label="Every",
        status_field="whois_status",
        error_field="whois_error",
        dispatch=dispatch_whois_lookups,
    ),
    EnrichmentKind.DNS: Enrichment(
        kind=EnrichmentKind.DNS,
        label="DNS lookup",
        eligible=DNS_ELIGIBLE_TYPES,
        eligible_label="Domain and URL",
        status_field="dns_status",
        error_field="dns_error",
        dispatch=dispatch_dns_lookups,
    ),
    EnrichmentKind.BGP: Enrichment(
        kind=EnrichmentKind.BGP,
        label="BGP enrichment",
        eligible=BGP_ELIGIBLE_TYPES,
        eligible_label="IP, IP range and ASN",
        status_field="bgp_status",
        error_field=None,
        dispatch=dispatch_ripestat_enrichment,
    ),
}
