"""Tripwires: a saved query that notifies or starts a scan when a result matches it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.surface import SurfaceDimension

MAX_TRIPWIRES = 200
MAX_NAME = 80
MAX_ACTIONS = 4
MAX_CHANNELS = 20
MAX_SCOPE_IDS = 500
MAX_STAGES = 12

# rows a check keeps on its record
MAX_STORED_ROWS = 1_000
# rows a becomes-true comparison reads per side
MAX_DIFF_ROWS = 100_000
# rows a preview reads per run
PREVIEW_ROW_CAP = 5_000
# rows a message lists
SAMPLE_ROWS = 5
MAX_RUNS_PER_DAY = 5
LIVE_TRIP_SECONDS = 60
RECENT_DAYS = 30
MAX_BACKTEST_RUNS = 20
MAX_PREVIEW_TARGETS = 10
QUIET_RETENTION_DAYS = 30
TRIPWIRE_KEY = "_tripwire"
RUN_LABEL = "Tripwire"


class Trigger(StrEnum):
    SCAN_SETTLED = "scan_settled"
    SCAN_LIVE = "scan_live"


class FireOn(StrEnum):
    APPEARS = "appears"
    BECOMES_TRUE = "becomes_true"
    MATCHES = "matches"


class ScopeKind(StrEnum):
    ALL = "all"
    TARGETS = "targets"
    ORGANIZATION = "organization"
    TAG = "tag"


class ActionKind(StrEnum):
    NOTIFY = "notify"
    SCAN = "scan"


class CheckStatus(StrEnum):
    FIRED = "fired"
    QUIET = "quiet"
    NO_BASELINE = "no_baseline"
    NOT_COVERED = "not_covered"
    ERROR = "error"


class OutcomeStatus(StrEnum):
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


TRIGGER_ORDER: tuple[str, ...] = (Trigger.SCAN_SETTLED.value, Trigger.SCAN_LIVE.value)
TRIGGER_LABELS: dict[str, str] = {
    Trigger.SCAN_SETTLED.value: "After a scan",
    Trigger.SCAN_LIVE.value: "During a scan",
}
TRIGGER_HELP: dict[str, str] = {
    Trigger.SCAN_SETTLED.value: "Checked when a run settles.",
    Trigger.SCAN_LIVE.value: "Checked as results land, and again when the run settles.",
}

FIRE_ON_ORDER: tuple[str, ...] = (
    FireOn.APPEARS.value,
    FireOn.BECOMES_TRUE.value,
    FireOn.MATCHES.value,
)
FIRE_ON_LABELS: dict[str, str] = {
    FireOn.APPEARS.value: "Appears",
    FireOn.BECOMES_TRUE.value: "Becomes true",
    FireOn.MATCHES.value: "Matches",
}
FIRE_ON_HELP: dict[str, str] = {
    FireOn.APPEARS.value: "A matching row no earlier scan of the target held.",
    FireOn.BECOMES_TRUE.value: "A row that matches now and did not match on the previous run.",
    FireOn.MATCHES.value: "Every run with a matching row.",
}
# a row a fire mode reports on, as the message names it
FIRE_ON_VERB: dict[str, str] = {
    FireOn.APPEARS.value: "appeared",
    FireOn.BECOMES_TRUE.value: "became true",
    FireOn.MATCHES.value: "matched",
}
# the same after "would have"
FIRE_ON_PARTICIPLE: dict[str, str] = {
    FireOn.APPEARS.value: "appeared",
    FireOn.BECOMES_TRUE.value: "become true",
    FireOn.MATCHES.value: "matched",
}

SCOPE_LABELS: dict[str, str] = {
    ScopeKind.ALL.value: "All targets",
    ScopeKind.TARGETS.value: "Targets",
    ScopeKind.ORGANIZATION.value: "Organization",
    ScopeKind.TAG.value: "Tag",
}

ACTION_ORDER: tuple[str, ...] = (ActionKind.NOTIFY.value, ActionKind.SCAN.value)
ACTION_LABELS: dict[str, str] = {
    ActionKind.NOTIFY.value: "Notify",
    ActionKind.SCAN.value: "Focused scan",
}
ACTION_HELP: dict[str, str] = {
    ActionKind.NOTIFY.value: "One message per run. Without a chosen channel, the channels subscribed to Tripwires receive it.",
    ActionKind.SCAN.value: f"Runs the chosen stages against the rows that fired. {MAX_RUNS_PER_DAY} runs a day.",
}

CHECK_STATUS_LABELS: dict[str, str] = {
    CheckStatus.FIRED.value: "Fired",
    CheckStatus.QUIET.value: "Not fired",
    CheckStatus.NO_BASELINE.value: "First scan",
    CheckStatus.NOT_COVERED.value: "Not scanned",
    CheckStatus.ERROR.value: "Error",
}
FIRST_SCAN_DETAIL = "First scan of the target."
NOT_COVERED_DETAIL = "The run did not scan this dimension."

OUTCOME_LABELS: dict[str, str] = {
    OutcomeStatus.DONE.value: "Done",
    OutcomeStatus.SKIPPED.value: "Skipped",
    OutcomeStatus.FAILED.value: "Failed",
}


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    dimension: str
    query: str
    fire_on: str
    trigger: str = Trigger.SCAN_SETTLED.value


TEMPLATE_GROUPS: tuple[tuple[str, str], ...] = (
    (FireOn.APPEARS.value, FIRE_ON_LABELS[FireOn.APPEARS.value]),
    (FireOn.BECOMES_TRUE.value, FIRE_ON_LABELS[FireOn.BECOMES_TRUE.value]),
    (Trigger.SCAN_LIVE.value, TRIGGER_LABELS[Trigger.SCAN_LIVE.value]),
)

TEMPLATES: tuple[Template, ...] = (
    Template(
        "new_web_assets",
        "New web assets",
        SurfaceDimension.WEB_ASSETS.value,
        "is:web",
        FireOn.APPEARS.value,
    ),
    Template(
        "remote_access",
        "Remote access portals",
        SurfaceDimension.WEB_ASSETS.value,
        "host:[vpn,sslvpn,citrix,remote,gateway] is:web",
        FireOn.APPEARS.value,
    ),
    Template(
        "developer_tooling",
        "Developer tooling",
        SurfaceDimension.WEB_ASSETS.value,
        "tech:[jenkins,gitlab,grafana,kibana,sonarqube] status:200",
        FireOn.APPEARS.value,
    ),
    Template(
        "non_production",
        "Staging and dev names",
        SurfaceDimension.WEB_ASSETS.value,
        "host:[staging,stg,dev,uat,test] is:web",
        FireOn.APPEARS.value,
    ),
    Template(
        "management_services",
        "Management services",
        SurfaceDimension.SERVICES.value,
        "service:[ssh,rdp,vnc,telnet]",
        FireOn.APPEARS.value,
    ),
    Template(
        "datastores",
        "Datastores on the internet",
        SurfaceDimension.SERVICES.value,
        "service:[mysql,postgresql,redis,mongodb,elasticsearch]",
        FireOn.APPEARS.value,
    ),
    Template(
        "sensitive_paths",
        "Sensitive paths",
        SurfaceDimension.ENDPOINTS.value,
        "is:sensitive",
        FireOn.APPEARS.value,
    ),
    Template(
        "exposed_secrets",
        "Secrets in responses",
        SurfaceDimension.SECRETS.value,
        "is:exposed",
        FireOn.APPEARS.value,
    ),
    Template(
        "exploited_software",
        "Known exploited software",
        SurfaceDimension.SOFTWARE.value,
        "is:kev",
        FireOn.APPEARS.value,
    ),
    Template(
        "answers_200",
        "Starts answering 200",
        SurfaceDimension.WEB_ASSETS.value,
        "status:200",
        FireOn.BECOMES_TRUE.value,
    ),
    Template(
        "origin_exposed",
        "Origin without a CDN",
        SurfaceDimension.WEB_ASSETS.value,
        "-is:cdn is:web",
        FireOn.BECOMES_TRUE.value,
    ),
    Template(
        "mail_spoofable",
        "DMARC missing",
        SurfaceDimension.WEB_ASSETS.value,
        "posture:dmarc_missing",
        FireOn.BECOMES_TRUE.value,
    ),
    Template(
        "critical_findings",
        "Critical findings",
        SurfaceDimension.VULNERABILITIES.value,
        "severity:critical",
        FireOn.APPEARS.value,
        Trigger.SCAN_LIVE.value,
    ),
    Template(
        "kev_findings",
        "Known exploited findings",
        SurfaceDimension.VULNERABILITIES.value,
        "is:kev",
        FireOn.APPEARS.value,
        Trigger.SCAN_LIVE.value,
    ),
    Template(
        "proven_findings",
        "Out-of-band callbacks",
        SurfaceDimension.VULNERABILITIES.value,
        "is:proven",
        FireOn.APPEARS.value,
        Trigger.SCAN_LIVE.value,
    ),
)


def template_group(template: Template) -> str:
    if template.trigger == Trigger.SCAN_LIVE.value:
        return Trigger.SCAN_LIVE.value
    return template.fire_on


def appears_query(query: str) -> str:
    """The query narrowed to rows no earlier scan of the target held."""
    text = query.strip()
    return f"({text}) is:new" if text else "is:new"


def run_label(count: int, noun: str, noun_plural: str) -> str:
    return f"{RUN_LABEL} · {count} {noun if count == 1 else noun_plural}"


__all__ = [
    "ACTION_HELP",
    "ACTION_LABELS",
    "ACTION_ORDER",
    "CHECK_STATUS_LABELS",
    "FIRE_ON_HELP",
    "FIRE_ON_LABELS",
    "FIRE_ON_ORDER",
    "FIRE_ON_PARTICIPLE",
    "FIRE_ON_VERB",
    "FIRST_SCAN_DETAIL",
    "LIVE_TRIP_SECONDS",
    "MAX_ACTIONS",
    "MAX_BACKTEST_RUNS",
    "MAX_CHANNELS",
    "MAX_DIFF_ROWS",
    "MAX_NAME",
    "MAX_PREVIEW_TARGETS",
    "MAX_RUNS_PER_DAY",
    "MAX_SCOPE_IDS",
    "MAX_STAGES",
    "MAX_STORED_ROWS",
    "MAX_TRIPWIRES",
    "NOT_COVERED_DETAIL",
    "OUTCOME_LABELS",
    "PREVIEW_ROW_CAP",
    "QUIET_RETENTION_DAYS",
    "RECENT_DAYS",
    "RUN_LABEL",
    "SAMPLE_ROWS",
    "SCOPE_LABELS",
    "TEMPLATES",
    "TEMPLATE_GROUPS",
    "TRIGGER_HELP",
    "TRIGGER_LABELS",
    "TRIGGER_ORDER",
    "TRIPWIRE_KEY",
    "ActionKind",
    "CheckStatus",
    "FireOn",
    "OutcomeStatus",
    "ScopeKind",
    "Template",
    "Trigger",
    "appears_query",
    "run_label",
    "template_group",
]
