"""Investigate: an agent that verifies one finding and records a verdict."""

from __future__ import annotations

from enum import StrEnum

from shared.definitions.ai import AIOffCode, off_reasons
from shared.definitions.surface import SurfaceDimension

INVESTIGATE_FEATURE = "investigate"
INVESTIGATE_CLIENT = "investigate"

# the dimension Investigate runs on
INVESTIGATE_DIMENSION = SurfaceDimension.VULNERABILITIES.value


# ---------- the verdict ----------


class Verdict(StrEnum):
    PENDING = "pending"
    REPRODUCED = "reproduced"
    CONFIRMED = "confirmed"
    NOT_REPRODUCED = "not_reproduced"
    FALSE_POSITIVE = "false_positive"
    NEEDS_PERSON = "needs_person"


VERDICT_LABELS: dict[str, str] = {
    Verdict.PENDING.value: "Open",
    Verdict.REPRODUCED.value: "Reproduced",
    Verdict.CONFIRMED.value: "Confirmed from evidence",
    Verdict.NOT_REPRODUCED.value: "Not reproduced",
    Verdict.FALSE_POSITIVE.value: "False positive",
    Verdict.NEEDS_PERSON.value: "Needs a person",
}

VERDICT_HELP: dict[str, str] = {
    Verdict.PENDING.value: "No verdict yet.",
    Verdict.REPRODUCED.value: "The check ran again and matched.",
    Verdict.CONFIRMED.value: "The stored evidence is conclusive on its own.",
    Verdict.NOT_REPRODUCED.value: "The check ran again and did not match.",
    Verdict.FALSE_POSITIVE.value: "The stored evidence contradicts the match.",
    Verdict.NEEDS_PERSON.value: "Verification needs a step the agent does not take.",
}

# verdicts that set the verification stamp
VERIFIED_VERDICTS: frozenset[str] = frozenset(
    {Verdict.REPRODUCED.value, Verdict.CONFIRMED.value}
)


def verdict_label(value: str | None) -> str:
    return VERDICT_LABELS.get(value or "", VERDICT_LABELS[Verdict.PENDING.value])


def is_verified(value: str | None) -> bool:
    return value in VERIFIED_VERDICTS


# ---------- a proposed action ----------


class PlanKind(StrEnum):
    # the finding's own check, on the host it was found on
    REPLAY = "replay"
    # a named check on an in-scope host the agent reasoned toward
    CHECK = "check"


PLAN_LABELS: dict[str, str] = {
    PlanKind.REPLAY.value: "Replay the check",
    PlanKind.CHECK.value: "Run a check",
}


class PlanState(StrEnum):
    PROPOSED = "proposed"
    REFUSED = "refused"
    APPROVED = "approved"
    RUNNING = "running"
    DONE = "done"
    DECLINED = "declined"
    FAILED = "failed"


PLAN_STATE_LABELS: dict[str, str] = {
    PlanState.PROPOSED.value: "Proposed",
    PlanState.REFUSED.value: "Refused",
    PlanState.APPROVED.value: "Approved",
    PlanState.RUNNING.value: "Running",
    PlanState.DONE.value: "Done",
    PlanState.DECLINED.value: "Declined",
    PlanState.FAILED.value: "Failed",
}


class PlanResult(StrEnum):
    REPRODUCED = "reproduced"
    NOT_REPRODUCED = "not_reproduced"
    ERROR = "error"


PLAN_RESULT_LABELS: dict[str, str] = {
    PlanResult.REPRODUCED.value: "Reproduced",
    PlanResult.NOT_REPRODUCED.value: "Not reproduced",
    PlanResult.ERROR.value: "Did not run",
}


# ---------- why a plan is refused ----------


class RefusalReason(StrEnum):
    INTRUSIVE = "intrusive"
    DOS = "dos"
    FUZZ = "fuzz"
    CALLBACK = "callback"
    CREDENTIALS = "credentials"
    OUT_OF_SCOPE = "out_of_scope"
    REQUESTS = "requests"
    BUDGET = "budget"


REFUSAL_LABELS: dict[str, str] = {
    RefusalReason.INTRUSIVE.value: "Tagged intrusive",
    RefusalReason.DOS.value: "Tagged for denial of service",
    RefusalReason.FUZZ.value: "Fuzzes the target",
    RefusalReason.CALLBACK.value: "Needs a callback",
    RefusalReason.CREDENTIALS.value: "Sends credentials",
    RefusalReason.OUT_OF_SCOPE.value: "Host is not under this target",
    RefusalReason.REQUESTS.value: "Sends too many requests",
    RefusalReason.BUDGET.value: "Request budget is spent",
}

REFUSAL_HELP: dict[str, str] = {
    RefusalReason.INTRUSIVE.value: "The check is tagged intrusive and runs only by hand.",
    RefusalReason.DOS.value: "The check is tagged for denial of service.",
    RefusalReason.FUZZ.value: "The check fuzzes parameters and runs only by hand.",
    RefusalReason.CALLBACK.value: "The check proves itself through a callback listener that is not configured.",
    RefusalReason.CREDENTIALS.value: "The check authenticates against the target.",
    RefusalReason.OUT_OF_SCOPE.value: "The host does not sit under the finding's target.",
    RefusalReason.REQUESTS.value: "The check sends more requests than a replay allows.",
    RefusalReason.BUDGET.value: "The investigation reached its request budget.",
}

# nuclei tags that keep a check out of an automatic replay
REFUSED_TAGS: dict[str, RefusalReason] = {
    "intrusive": RefusalReason.INTRUSIVE,
    "dos": RefusalReason.DOS,
    "fuzz": RefusalReason.FUZZ,
    "fuzzing": RefusalReason.FUZZ,
}

# nuclei tags for a check that authenticates against the target
CREDENTIAL_TAGS: frozenset[str] = frozenset(
    {"default-login", "default-logins", "brute-force", "bruteforce", "creds-stuffing"}
)


def tag_refusal(tags: frozenset[str] | set[str]) -> RefusalReason | None:
    """The reason a check's tags keep it out of a replay, or None."""
    for tag in tags:
        reason = REFUSED_TAGS.get(tag.lower())
        if reason is not None:
            return reason
    return None


# ---------- budgets ----------

# the most requests one replay's template may send
MAX_PLAN_REQUESTS = 10
# the most requests an investigation spends across its approved plans
MAX_INVESTIGATION_REQUESTS = 40
# the most plans one investigation proposes
MAX_PLANS = 8
# the most known-exploited findings the replay rule acts on per scan
MAX_RULE_REPLAYS = 25
MAX_TOOL_ROUNDS = 8
MAX_CALLS_PER_ROUND = 3
RATE_PER_MINUTE = 6

MAX_RATIONALE_CHARS = 2_000
MAX_PLAN_REASON_CHARS = 280
MAX_HOST = 255
MAX_TEMPLATE_ID = 200


# ---------- streaming ----------


class StreamEvent(StrEnum):
    TRACE = "trace"
    DELTA = "delta"
    DONE = "done"
    ERROR = "error"


# ---------- availability ----------


InvestigateOffCode = AIOffCode
INVESTIGATE_OFF_REASONS: dict[str, str] = off_reasons("Investigate")
