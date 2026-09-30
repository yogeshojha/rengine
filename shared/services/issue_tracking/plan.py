"""Which findings become which issues: one each, grouped by check, or added to an open issue."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from shared.definitions.issue_trackers import (
    MAX_GROUP_LOCATIONS,
    Grouping,
    files_alone,
)
from shared.definitions.vulnerabilities import severity_rank

Key = tuple[uuid.UUID, str]


@dataclass
class OpenIssue:
    id: uuid.UUID
    key: str | None
    locations: int


@dataclass
class NewIssue:
    target_id: uuid.UUID
    template_id: str
    grouped: bool
    vulns: list[Any]

    @property
    def severity(self) -> str:
        return min((v.severity for v in self.vulns), key=severity_rank)


@dataclass
class Attachment:
    issue: OpenIssue
    vulns: list[Any]


@dataclass
class Plan:
    new: list[NewIssue] = field(default_factory=list)
    attach: list[Attachment] = field(default_factory=list)
    already_filed: int = 0

    @property
    def findings(self) -> int:
        return sum(len(i.vulns) for i in self.new) + sum(
            len(a.vulns) for a in self.attach
        )


def plan_filing(
    vulns: Iterable[Any],
    *,
    grouping: Grouping,
    filed: set[Key],
    open_groups: Mapping[Key, OpenIssue],
) -> Plan:
    """One vuln per (target_id, fingerprint). filed and open_groups belong to one tracker."""
    plan = Plan()
    buckets: dict[Key, list[Any]] = {}
    for vuln in vulns:
        if (vuln.target_id, vuln.fingerprint) in filed:
            plan.already_filed += 1
            continue
        alone = grouping == Grouping.SEPARATE or files_alone(
            vuln.severity, is_kev=bool(vuln.is_kev), evidence=vuln.evidence
        )
        if alone:
            plan.new.append(NewIssue(vuln.target_id, vuln.template_id, False, [vuln]))
        else:
            buckets.setdefault((vuln.target_id, vuln.template_id), []).append(vuln)
    for key, bucket in buckets.items():
        members = sorted(bucket, key=lambda v: v.matched_at or "")
        existing = open_groups.get(key)
        if existing is not None:
            room = max(0, MAX_GROUP_LOCATIONS - existing.locations)
            if room:
                plan.attach.append(Attachment(existing, members[:room]))
                members = members[room:]
        for start in range(0, len(members), MAX_GROUP_LOCATIONS):
            chunk = members[start : start + MAX_GROUP_LOCATIONS]
            plan.new.append(NewIssue(key[0], key[1], True, chunk))
    plan.new.sort(key=lambda i: (severity_rank(i.severity), i.template_id))
    return plan
