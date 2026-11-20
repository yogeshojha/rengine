"""Tripwires: a saved query that notifies or starts a scan when a result matches it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.infostealer import ANY as ANY_AUDIENCE
from shared.definitions.infostealer import Audience
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
    DAILY = "daily"


class Source(StrEnum):
    LEAKED_LOGINS = "leaked_logins"


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


TRIGGER_ORDER: tuple[str, ...] = (
    Trigger.SCAN_SETTLED.value,
    Trigger.SCAN_LIVE.value,
    Trigger.DAILY.value,
)
TRIGGER_LABELS: dict[str, str] = {
    Trigger.SCAN_SETTLED.value: "After a scan",
    Trigger.SCAN_LIVE.value: "During a scan",
    Trigger.DAILY.value: "Daily",
}
TRIGGER_HELP: dict[str, str] = {
    Trigger.SCAN_SETTLED.value: "Checked when a run settles.",
    Trigger.SCAN_LIVE.value: "Checked as results land, and again when the run settles.",
    Trigger.DAILY.value: "Checked once a day, with no scan.",
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
    FireOn.BECOMES_TRUE.value: "started matching",
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
    ActionKind.SCAN.value: f"Runs the chosen stages against the rows that fired. At most {MAX_RUNS_PER_DAY} runs a day.",
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


# ---------- daily sources ----------


@dataclass(frozen=True)
class SourceOption:
    key: str
    label: str
    help: str = ""


@dataclass(frozen=True)
class SourceField:
    key: str
    label: str
    options: tuple[SourceOption, ...]
    default: str


@dataclass(frozen=True)
class SourceSpec:
    key: str
    label: str
    help: str
    dimension: str
    noun: str
    noun_plural: str
    fields: tuple[SourceField, ...] = ()


AUDIENCE_PARAM = "audience"

SOURCES: dict[str, SourceSpec] = {
    Source.LEAKED_LOGINS.value: SourceSpec(
        key=Source.LEAKED_LOGINS.value,
        label="Leaked logins",
        help="Logins for the target's domain found in infostealer logs.",
        dimension=SurfaceDimension.WEB_ASSETS.value,
        noun="change",
        noun_plural="changes",
        fields=(
            SourceField(
                key=AUDIENCE_PARAM,
                label="Audience",
                options=(
                    SourceOption(ANY_AUDIENCE, "Employees and users"),
                    SourceOption(
                        Audience.EMPLOYEE.value,
                        "Employees",
                        "Machines of the organization's staff.",
                    ),
                    SourceOption(
                        Audience.USER.value,
                        "Users",
                        "Machines of people with an account on the domain.",
                    ),
                ),
                default=ANY_AUDIENCE,
            ),
        ),
    ),
}
SOURCE_ORDER: tuple[str, ...] = tuple(SOURCES)
SOURCE_REQUIRED = "Choose what the daily check reads."
DAILY_QUIET_DETAIL = "The change is outside the chosen audience."
DAILY_NOT_SCANNED = "No completed scan of the target."


def clean_params(source: str, params: dict | None) -> dict[str, str]:
    """The source's fields with defaults filled. Raises ValueError on an unknown key or value."""
    spec = SOURCES[source]
    given = dict(params or {})
    out: dict[str, str] = {}
    for field in spec.fields:
        value = given.pop(field.key, field.default)
        if value not in {option.key for option in field.options}:
            msg = f"Unknown {field.label.lower()} '{value}'."
            raise ValueError(msg)
        out[field.key] = value
    if given:
        msg = f"Unknown setting '{next(iter(given))}'."
        raise ValueError(msg)
    return out


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    dimension: str
    query: str
    fire_on: str
    trigger: str = Trigger.SCAN_SETTLED.value
    source: str | None = None


TEMPLATE_GROUPS: tuple[tuple[str, str], ...] = (
    (FireOn.APPEARS.value, FIRE_ON_LABELS[FireOn.APPEARS.value]),
    (FireOn.BECOMES_TRUE.value, FIRE_ON_LABELS[FireOn.BECOMES_TRUE.value]),
    (Trigger.SCAN_LIVE.value, TRIGGER_LABELS[Trigger.SCAN_LIVE.value]),
    (Trigger.DAILY.value, TRIGGER_LABELS[Trigger.DAILY.value]),
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
    Template(
        "leaked_logins",
        "New leaked logins",
        SurfaceDimension.WEB_ASSETS.value,
        "",
        FireOn.APPEARS.value,
        Trigger.DAILY.value,
        Source.LEAKED_LOGINS.value,
    ),
)

SCAN_TRIGGERS: frozenset[str] = frozenset(
    {Trigger.SCAN_SETTLED.value, Trigger.SCAN_LIVE.value}
)


def template_group(template: Template) -> str:
    if template.trigger != Trigger.SCAN_SETTLED.value:
        return template.trigger
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
    "AUDIENCE_PARAM",
    "CHECK_STATUS_LABELS",
    "DAILY_NOT_SCANNED",
    "DAILY_QUIET_DETAIL",
    "FIRE_ON_HELP",
    "FIRE_ON_LABELS",
    "FIRE_ON_ORDER",
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
    "PREVIEW_ROW_CAP",
    "QUIET_RETENTION_DAYS",
    "RECENT_DAYS",
    "RUN_LABEL",
    "SAMPLE_ROWS",
    "SCAN_TRIGGERS",
    "SCOPE_LABELS",
    "SOURCES",
    "SOURCE_ORDER",
    "SOURCE_REQUIRED",
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
    "Source",
    "SourceField",
    "SourceOption",
    "SourceSpec",
    "Template",
    "Trigger",
    "appears_query",
    "clean_params",
    "run_label",
    "template_group",
]
