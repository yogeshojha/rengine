"""What an MCP token may do. One definition; the frontend mirrors it."""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    READ = "read"
    PLAN = "plan"
    WRITE = "write"
    LAUNCH = "launch"


CAPABILITY_ORDER: tuple[str, ...] = tuple(c.value for c in Capability)

CAPABILITY_LABELS: dict[str, str] = {
    Capability.READ.value: "Read",
    Capability.PLAN.value: "Plan",
    Capability.WRITE.value: "Write",
    Capability.LAUNCH.value: "Launch",
}

CAPABILITY_HELP: dict[str, str] = {
    Capability.READ.value: "Query assets, services, endpoints, findings and coverage.",
    Capability.PLAN.value: "Resolve a scan plan without running it. Touches no target.",
    Capability.WRITE.value: "Record triage decisions on findings.",
    Capability.LAUNCH.value: "Start scans and focused rescans against targets.",
}

# read is granted to every token; a token with no capability at all is useless
ALWAYS_GRANTED: tuple[str, ...] = (Capability.READ.value,)

# the only capability that reaches a machine the operator does not own
TOUCHES_TARGETS: tuple[str, ...] = (Capability.LAUNCH.value,)

DEFAULT_CEILING: dict[str, bool] = {
    Capability.READ.value: True,
    Capability.PLAN.value: True,
    Capability.WRITE.value: True,
    Capability.LAUNCH.value: False,
}


def normalize(values: list[str] | tuple[str, ...] | None) -> list[str]:
    """Drop unknown names, always include read, and keep the declared order."""
    given = {v for v in (values or []) if v in CAPABILITY_ORDER}
    given.update(ALWAYS_GRANTED)
    return [c for c in CAPABILITY_ORDER if c in given]


def within_ceiling(values: list[str], ceiling: dict[str, bool]) -> list[str]:
    return [
        c for c in normalize(values) if ceiling.get(c, False) or c in ALWAYS_GRANTED
    ]
