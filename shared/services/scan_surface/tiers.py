"""Split a template selection into the tiers the budget is spent in."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from shared.definitions.oast import OAST_TAG
from shared.definitions.scan_surface import (
    BLIND_SWEEP_REQUESTS,
    MAX_TECH_GROUPS,
    ONE_REQUEST_PATHS,
    SWEEP_REQUEST_CAP,
    is_universal,
    product_tags,
)
from shared.definitions.vulnerabilities import (
    SEVERITY_RANK,
    Protocol,
    is_kev,
    is_vkev,
)

HTTP_PROTOCOLS: frozenset[str] = frozenset(
    {Protocol.HTTP.value, Protocol.HEADLESS.value}
)
SERVICE_PROTOCOLS: frozenset[str] = frozenset(
    {Protocol.NETWORK.value, Protocol.SSL.value, Protocol.JAVASCRIPT.value}
)
NAME_PROTOCOLS: frozenset[str] = frozenset({Protocol.DNS.value})

# nuclei -type values per protocol group
SERVICE_TYPES: tuple[str, ...] = ("tcp", "ssl", "javascript")
NAME_TYPES: tuple[str, ...] = ("dns",)


@dataclass
class TierPlan:
    one_request: list = field(default_factory=list)
    universal: list = field(default_factory=list)
    product: list = field(default_factory=list)
    oast: list = field(default_factory=list)
    services: list = field(default_factory=list)
    names: list = field(default_factory=list)
    unrunnable: list = field(default_factory=list)
    top_paths: list[str] = field(default_factory=list)

    def matched(self, tags: Iterable[str]) -> list:
        wanted = {t.lower() for t in tags}
        if not wanted:
            return []
        return [row for row in self.product if product_tags(row.tags) & wanted]


def top_paths(rows: Iterable, limit: int = ONE_REQUEST_PATHS) -> list[str]:
    """The request paths most checks share, root first."""
    counts: Counter[str] = Counter()
    for row in rows:
        if not getattr(row, "simple", False):
            continue
        for path in getattr(row, "paths", None) or ():
            counts[path] += 1
    return [path for path, _ in counts.most_common(limit)]


def wants_callback(row) -> bool:
    """A check nuclei refuses to run with no out-of-band client behind it."""
    if getattr(row, "needs_oast", False):
        return True
    return OAST_TAG in {str(t).lower() for t in getattr(row, "tags", None) or ()}


def split(rows: Iterable) -> TierPlan:
    """Assign every selected check to exactly one tier."""
    plan = TierPlan()
    listed = list(rows)
    plan.top_paths = top_paths(listed)
    top = set(plan.top_paths)
    for row in listed:
        protocol = row.protocol
        if protocol in SERVICE_PROTOCOLS:
            plan.services.append(row)
            continue
        if protocol in NAME_PROTOCOLS:
            plan.names.append(row)
            continue
        if protocol not in HTTP_PROTOCOLS:
            plan.unrunnable.append(row)
            continue
        if wants_callback(row):
            plan.oast.append(row)
            continue
        paths = getattr(row, "paths", None) or []
        if getattr(row, "simple", False) and paths and set(paths) <= top:
            plan.one_request.append(row)
        elif is_universal(row.tags) and requests_of(row) <= SWEEP_REQUEST_CAP:
            plan.universal.append(row)
        else:
            plan.product.append(row)
    return plan


@dataclass
class TechGroup:
    tags: frozenset[str]
    items: list = field(default_factory=list)
    rows: list = field(default_factory=list)


def tech_groups(
    items: Iterable, plan: TierPlan, limit: int = MAX_TECH_GROUPS
) -> list[TechGroup]:
    """Representatives sharing the detected-software tags, one invocation each."""
    by_tags: dict[frozenset[str], TechGroup] = {}
    for item in items:
        tags = frozenset(t.lower() for t in getattr(item, "tags", ()) or ())
        if not tags:
            continue
        group = by_tags.setdefault(tags, TechGroup(tags=tags))
        group.items.append(item)
    groups = sorted(by_tags.values(), key=lambda g: (-len(g.items), sorted(g.tags)))
    if len(groups) > limit:
        keep, rest = groups[: limit - 1], groups[limit - 1 :]
        mixed = TechGroup(tags=frozenset().union(*(g.tags for g in rest)))
        for group in rest:
            mixed.items.extend(group.items)
        groups = [*keep, mixed]
    out: list[TechGroup] = []
    for group in groups:
        group.rows = plan.matched(group.tags)
        if group.rows:
            out.append(group)
    return out


def requests_of(row) -> int:
    """What one check costs against one host."""
    return max(1, int(getattr(row, "requests", 1) or 1))


def _blind_rank(row) -> tuple:
    """Known-exploited first, then severity, then cheapest."""
    tags = getattr(row, "tags", None)
    return (
        0 if is_kev(tags) else 1 if is_vkev(tags) else 2,
        SEVERITY_RANK.get(getattr(row, "severity", ""), len(SEVERITY_RANK)),
        requests_of(row),
    )


def blind_order(rows: Iterable) -> list:
    """The product checks ranked known-exploited first, then severity, then cheapest."""
    return sorted(rows, key=_blind_rank)


def blind_core(rows: Iterable, budget: int = BLIND_SWEEP_REQUESTS) -> list:
    """The product checks worth sweeping where the software was never identified."""
    out: list = []
    spent = 0
    for row in blind_order(rows):
        price = requests_of(row)
        if price > SWEEP_REQUEST_CAP or spent + price > budget:
            continue
        out.append(row)
        spent += price
    return out


def cost(rows: Iterable) -> int:
    """Requests per host, an upper bound before nuclei clusters."""
    return sum(requests_of(row) for row in rows)


__all__ = [
    "HTTP_PROTOCOLS",
    "NAME_PROTOCOLS",
    "NAME_TYPES",
    "SERVICE_PROTOCOLS",
    "SERVICE_TYPES",
    "TechGroup",
    "TierPlan",
    "blind_core",
    "blind_order",
    "cost",
    "requests_of",
    "split",
    "tech_groups",
    "top_paths",
]
