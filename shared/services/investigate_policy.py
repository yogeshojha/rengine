"""Whether a proposed plan may run, read once over the facts the caller gathers."""

from __future__ import annotations

from dataclasses import dataclass

from shared.definitions.investigate import (
    MAX_PLAN_REQUESTS,
    RefusalReason,
    tag_refusal,
)

# nuclei tags for a check that authenticates against the target
CREDENTIAL_TAGS: frozenset[str] = frozenset(
    {"default-login", "default-logins", "brute-force", "bruteforce", "creds-stuffing"}
)


@dataclass(frozen=True)
class PlanInput:
    tags: frozenset[str]
    # the check proves itself through a callback listener
    needs_callback: bool
    # a callback listener is configured for the instance
    oast_ready: bool
    # the template's own request estimate
    request_count: int | None
    # the host sits under the finding's target
    in_scope: bool
    # requests left in the investigation's budget
    budget_remaining: int


def plan_cost(request_count: int | None) -> int:
    """How many requests a plan spends against the budget."""
    return request_count if request_count else 1


def refuses(plan: PlanInput) -> RefusalReason | None:
    """The reason a plan must not run automatically, or None."""
    if not plan.in_scope:
        return RefusalReason.OUT_OF_SCOPE
    tagged = tag_refusal(plan.tags)
    if tagged is not None:
        return tagged
    over_requests = (
        plan.request_count is not None and plan.request_count > MAX_PLAN_REQUESTS
    )
    checks: tuple[tuple[bool, RefusalReason], ...] = (
        (bool(plan.tags & CREDENTIAL_TAGS), RefusalReason.CREDENTIALS),
        (plan.needs_callback and not plan.oast_ready, RefusalReason.CALLBACK),
        (over_requests, RefusalReason.REQUESTS),
        (plan_cost(plan.request_count) > plan.budget_remaining, RefusalReason.BUDGET),
    )
    for failed, reason in checks:
        if failed:
            return reason
    return None
