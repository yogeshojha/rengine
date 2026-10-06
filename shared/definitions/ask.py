"""Ask: a read-only conversation on the estate, a finding or a web asset."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from shared.definitions.surface import SURFACE_NOUN, SurfaceDimension

ASK_CLIENT = "ask"
MAX_THREADS_PER_FINDING = 12
MAX_TITLE = 80
MAX_QUESTION_CHARS = 4_000
MAX_STARTERS = 3
MAX_ANSWER_CHARS = 12_000
HISTORY_TURNS = 12
HISTORY_CHARS = 16_000
EVIDENCE_CHARS = 6_000
TOOL_TEXT_CHARS = 12_000
MAX_TOOL_ROUNDS = 6
MAX_CITED_LINES = 6
MAX_FACT_DETAIL = 200
RATE_PER_MINUTE = 10
QUESTIONS_PER_DAY = 200
MAX_CALLS_PER_ROUND = 3


class Verdict(StrEnum):
    PROFILE = "profile"
    PROVEN = "proven"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"
    INSUFFICIENT = "insufficient"
    FALSE_POSITIVE = "false_positive"


VERDICT_LABELS: dict[str, str] = {
    Verdict.PROFILE.value: "Profile",
    Verdict.PROVEN.value: "Proven",
    Verdict.LIKELY.value: "Likely real",
    Verdict.UNCERTAIN.value: "Uncertain",
    Verdict.INSUFFICIENT.value: "Not enough evidence",
    Verdict.FALSE_POSITIVE.value: "Marked false positive",
}


class FactTone(StrEnum):
    FOR = "for"
    AGAINST = "against"
    UNKNOWN = "unknown"


class CitationKind(StrEnum):
    FACT = "fact"
    TOOL = "tool"
    LINE = "line"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class EvidenceField(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    TITLE = "title"
    NOTE = "note"
    MATCHED_AT = "matched_at"


class StreamEvent(StrEnum):
    TRACE = "trace"
    DELTA = "delta"
    BLOCK = "block"
    DONE = "done"
    ERROR = "error"


class TraceStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class AskFlag(StrEnum):
    INSTRUCTION_TEXT = "instruction_text"


class Decision(StrEnum):
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    NONE = "none"


class NextStep(StrEnum):
    FILE_ISSUE = "file_issue"
    RESCAN = "rescan"
    NONE = "none"


SUGGESTION = re.compile(r"\s*>>\s*decision=(\w+)\s+next=(\w+)\s*$")


SECRET_TAGS: frozenset[str] = frozenset(
    {
        "token",
        "tokens",
        "secret",
        "secrets",
        "key",
        "keys",
        "apikey",
        "api-key",
        "credential",
        "credentials",
        "creds",
        "password",
        "passwords",
        "exposure",
        "disclosure",
        "leak",
    }
)

ASK_DIMENSIONS: tuple[str, ...] = (
    SurfaceDimension.VULNERABILITIES.value,
    SurfaceDimension.WEB_ASSETS.value,
)

CITATION = re.compile(r"( ?)\[(F|T|R)(\d{1,3})\]")
CITATION_MARK = re.compile(r" ?\[\[(\d{1,2})\]\]")
# a row a person points at travels as dimension:value
ABOUT_SEPARATOR = ":"


# ---------- the estate ----------


class AskOffCode(StrEnum):
    SWITCHED_OFF = "switched_off"
    NO_PROVIDER = "no_provider"
    NO_KEY = "no_key"
    UNSUPPORTED = "unsupported"
    FEATURE_OFF = "feature_off"


ASK_OFF_REASONS: dict[str, str] = {
    AskOffCode.SWITCHED_OFF.value: "AI is switched off.",
    AskOffCode.NO_PROVIDER.value: "No AI provider is in use.",
    AskOffCode.NO_KEY.value: "No AI provider key is set.",
    AskOffCode.UNSUPPORTED.value: "The AI provider is not supported.",
    AskOffCode.FEATURE_OFF.value: "Ask is switched off in AI settings.",
}


class AskSubject(StrEnum):
    ASSET = "asset"
    ESTATE = "estate"


class BlockKind(StrEnum):
    ROWS = "rows"
    GROUPS = "groups"
    CVE = "cve"


MAX_ESTATE_THREADS = 300
EMPTY_THREAD_SECONDS = 900
LISTED_THREADS = 60
ESTATE_TOOL_ROUNDS = 8
INTELLIGENT_TOOL_ROUNDS = 12
ESTATE_CALLS_PER_ROUND = 4
MAX_BLOCKS_PER_ANSWER = 6
MAX_BLOCKS_PER_THREAD = 60
BLOCK_ROWS = 8
BLOCK_GROUPS = 12
BLOCK_SAMPLE = 6
MAX_BLOCK_QUERY = 2_000
MAX_BLOCK_TITLE = 120
MAX_SCOPE_VALUES = 40
MAX_FOLLOW_UPS = 4
MAX_FOLLOW_UP_CHARS = 140
MAX_ESTATE_STARTERS = 6
MAX_LOOKUP_VALUES = 12
STARTER_TTL_SECONDS = 120

BLOCK_REF = re.compile(r"\[(B\d{1,2})\]")
BLOCK_ID = re.compile(r"^B\d{1,2}$")


class FollowUpSource(StrEnum):
    PIVOT = "pivot"
    MODEL = "model"


class TargetKey(StrEnum):
    TARGET = "target"
    TAG = "tag"
    ORGANIZATION = "organization"


@dataclass(frozen=True)
class EstateStarter:
    key: str
    question: str
    # reads after the count; {noun} is the dimension's noun for that count
    statement: str
    dimension: str
    query: str
    # the group key whose largest group the starter names
    cause: str | None = None


# most needed first
ESTATE_STARTERS: tuple[EstateStarter, ...] = (
    EstateStarter(
        "kev",
        "Which findings are known exploited",
        "known exploited {noun}",
        SurfaceDimension.VULNERABILITIES.value,
        "is:kev",
        "ip",
    ),
    EstateStarter(
        "admin_open",
        "Which admin panels answer without a login",
        "{noun} with an admin panel and no login",
        SurfaceDimension.WEB_ASSETS.value,
        "exposure:admin_interface and not is:auth",
        "target",
    ),
    EstateStarter(
        "critical",
        "Which critical findings are not reviewed",
        "critical {noun} not reviewed",
        SurfaceDimension.VULNERABILITIES.value,
        "severity:critical and state:open",
        "ip",
    ),
    EstateStarter(
        "new_week",
        "Which web assets appeared in the last 7 days",
        "{noun} new in the last 7 days",
        SurfaceDimension.WEB_ASSETS.value,
        "is:new and discovered:<7d",
        "target",
    ),
    EstateStarter(
        "remote_admin",
        "Which services expose remote administration",
        "{noun} exposing remote administration",
        SurfaceDimension.SERVICES.value,
        "port:[22,23,3389,5900]",
        "port",
    ),
    EstateStarter(
        "stack_traces",
        "Which web assets leak a stack trace",
        "{noun} leaking a stack trace",
        SurfaceDimension.WEB_ASSETS.value,
        'body:traceback or body:"stack trace" or title:exception',
        "target",
    ),
    EstateStarter(
        "redirect_params",
        "Which endpoints take a redirect parameter",
        "{noun} taking a redirect parameter",
        SurfaceDimension.ENDPOINTS.value,
        "param:[redirect,url,next,return,returnurl,goto]",
        "host",
    ),
    EstateStarter(
        "dmarc",
        "Which web assets sit under a domain with no DMARC record",
        "{noun} under a domain with no DMARC record",
        SurfaceDimension.WEB_ASSETS.value,
        "posture:dmarc_missing",
        "target",
    ),
)
# a starter card names its largest group from this share up
STARTER_CAUSE_SHARE = 0.4


# ---------- what concentrates a set ----------


@dataclass(frozen=True)
class CauseKey:
    key: str
    one: str
    many: str
    # joins a row noun to a group value, as in "findings from <check>"
    prep: str = "on"
    # the group key read inside each cause
    detail: str | None = None
    # the network operator of an address
    who: bool = False
    # the value is an identifier set in mono
    mono: bool = False


_WEB = SURFACE_NOUN[SurfaceDimension.WEB_ASSETS.value]
_ADDRESS = SURFACE_NOUN[SurfaceDimension.IPS.value]

CAUSE_KEYS: dict[str, tuple[CauseKey, ...]] = {
    SurfaceDimension.VULNERABILITIES.value: (
        CauseKey("ip", "server", "servers", "on", "template", who=True, mono=True),
        CauseKey("template", "check", "checks", "from", "host", mono=True),
        CauseKey("host", *_WEB, "on", "template", mono=True),
        CauseKey("target", "target", "targets", "on", "template"),
    ),
    SurfaceDimension.WEB_ASSETS.value: (
        CauseKey("ip", *_ADDRESS, "on", "tech", who=True, mono=True),
        CauseKey(
            "cname", "CNAME target", "CNAME targets", "pointing at", "tech", mono=True
        ),
        CauseKey("title", "page title", "page titles", "titled", "target"),
        CauseKey("tech", "technology", "technologies", "running", "target"),
        CauseKey("target", "target", "targets", "on", "tech"),
    ),
    SurfaceDimension.SERVICES.value: (
        CauseKey("product", "product", "products", "running", "port"),
        CauseKey("ip", *_ADDRESS, "on", "service", who=True, mono=True),
        CauseKey("port", "port", "ports", "on", "product", mono=True),
        CauseKey("target", "target", "targets", "on", "service"),
    ),
    SurfaceDimension.ENDPOINTS.value: (
        CauseKey("host", *_WEB, "on", "dir", mono=True),
        CauseKey("dir", "directory", "directories", "in", "host", mono=True),
        CauseKey(
            "status", "status code", "status codes", "answering", "host", mono=True
        ),
        CauseKey("target", "target", "targets", "on", "host"),
    ),
    SurfaceDimension.IPS.value: (
        CauseKey(
            "org", "network operator", "network operators", "operated by", "country"
        ),
        CauseKey("asn", "network", "networks", "in", "country", mono=True),
        CauseKey("country", "country", "countries", "in", "org"),
        CauseKey("target", "target", "targets", "on", "org"),
    ),
}
MIN_CAUSE_ROWS = 4
# most groups in a cause, unless its largest holds FALLBACK_CAUSE_SHARE
MAX_CAUSE_GROUPS = 8
# share of the rows that must carry a value of the key
MIN_CAUSE_COVER = 0.8
FALLBACK_CAUSE_SHARE = 0.5
MAX_CAUSES = 5
CAUSE_DETAIL_ROWS = 5
CAUSE_DETAILS = 3


# ---------- counted facts within a set ----------


@dataclass(frozen=True)
class BlockFact:
    # reads after a count, as in "27 new in the latest scans"
    title: str
    question: str
    token: str


BLOCK_FACTS: dict[str, tuple[BlockFact, ...]] = {
    SurfaceDimension.VULNERABILITIES.value: (
        BlockFact("known exploited", "Which of these are known exploited", "is:kev"),
        BlockFact(
            "critical or high",
            "Which of these are critical or high",
            "severity:[critical,high]",
        ),
        BlockFact(
            "new in the latest scans",
            "Which of these are new in the latest scans",
            "is:new",
        ),
        BlockFact(
            "proven by a callback",
            "Which of these are proven by a callback",
            "is:proven",
        ),
        BlockFact("not reviewed", "Which of these are not reviewed", "is:open"),
    ),
    SurfaceDimension.WEB_ASSETS.value: (
        BlockFact(
            "with a known exploited finding",
            "Which of these carry a known exploited finding",
            "is:kev",
        ),
        BlockFact("with findings", "Which of these carry findings", "is:vulnerable"),
        BlockFact(
            "new in the latest scans",
            "Which of these are new in the latest scans",
            "is:new",
        ),
        BlockFact(
            "with an admin or database port open",
            "Which of these have an admin or database port open",
            "is:sensitive",
        ),
        BlockFact(
            "behind a login, 401 or 403",
            "Which of these are behind a login, 401 or 403",
            "is:auth",
        ),
    ),
    SurfaceDimension.SERVICES.value: (
        BlockFact(
            "with a known exploited finding",
            "Which of these carry a known exploited finding",
            "is:kev",
        ),
        BlockFact(
            "on admin or database ports",
            "Which of these are admin or database ports",
            "is:sensitive",
        ),
        BlockFact(
            "new in the latest scans",
            "Which of these are new in the latest scans",
            "is:new",
        ),
        BlockFact("with findings", "Which of these carry findings", "is:vulnerable"),
    ),
    SurfaceDimension.ENDPOINTS.value: (
        BlockFact("with findings", "Which of these carry findings", "is:vulnerable"),
        BlockFact("taking parameters", "Which of these take parameters", "is:param"),
        BlockFact("shaped as API routes", "Which of these are API routes", "is:api"),
        BlockFact(
            "answering 401 or 403", "Which of these answer 401 or 403", "is:auth"
        ),
        BlockFact(
            "new in the latest scans",
            "Which of these are new in the latest scans",
            "is:new",
        ),
    ),
    SurfaceDimension.IPS.value: (
        BlockFact(
            "with a known exploited finding",
            "Which of these carry a known exploited finding",
            "is:kev",
        ),
        BlockFact(
            "with an admin or database port open",
            "Which of these have an admin or database port open",
            "is:sensitive",
        ),
        BlockFact("behind a CDN", "Which of these sit behind a CDN", "is:cdn"),
        BlockFact(
            "new in the latest scans",
            "Which of these are new in the latest scans",
            "is:new",
        ),
    ),
    SurfaceDimension.SOFTWARE.value: (
        BlockFact("known exploited", "Which of these are known exploited", "is:kev"),
        BlockFact(
            "with a fixed version", "Which of these have a fixed version", "is:fixable"
        ),
        BlockFact(
            "cross-checked by a finding",
            "Which of these are cross-checked by a finding",
            "is:cross-checked",
        ),
    ),
}
MAX_FACTS = 4


# ---------- follow-ups from the largest group ----------


@dataclass(frozen=True)
class Pivot:
    # {value} is the largest group's value or the CVE id
    question: str
    title: str
    dimension: str
    field: str
    op: str = "="


PIVOTS: dict[tuple[str, str], tuple[Pivot, ...]] = {
    (SurfaceDimension.VULNERABILITIES.value, "ip"): (
        Pivot(
            "Which web assets resolve to {value}",
            "web assets on {value}",
            SurfaceDimension.WEB_ASSETS.value,
            "ip",
            "=",
        ),
        Pivot(
            "Which services are open on {value}",
            "services on {value}",
            SurfaceDimension.SERVICES.value,
            "ip",
            "=",
        ),
    ),
    (SurfaceDimension.VULNERABILITIES.value, "host"): (
        Pivot(
            "Which services are open on {value}",
            "services on {value}",
            SurfaceDimension.SERVICES.value,
            "host",
            "=",
        ),
        Pivot(
            "Which endpoints sit on {value}",
            "endpoints on {value}",
            SurfaceDimension.ENDPOINTS.value,
            "host",
            "=",
        ),
    ),
    (SurfaceDimension.WEB_ASSETS.value, "ip"): (
        Pivot(
            "Which services are open on {value}",
            "services on {value}",
            SurfaceDimension.SERVICES.value,
            "ip",
            "=",
        ),
        Pivot(
            "Which findings sit on {value}",
            "findings on {value}",
            SurfaceDimension.VULNERABILITIES.value,
            "ip",
            "=",
        ),
    ),
    (SurfaceDimension.WEB_ASSETS.value, "cname"): (
        Pivot(
            "Which web assets point at {value}",
            "web assets pointing at {value}",
            SurfaceDimension.WEB_ASSETS.value,
            "cname",
            "=",
        ),
    ),
    (SurfaceDimension.WEB_ASSETS.value, "tech"): (
        Pivot(
            "Which findings sit on {value} web assets",
            "findings on {value}",
            SurfaceDimension.VULNERABILITIES.value,
            "tech",
            "=",
        ),
    ),
    (SurfaceDimension.WEB_ASSETS.value, "target"): (
        Pivot(
            "Which findings sit on {value}",
            "findings on {value}",
            SurfaceDimension.VULNERABILITIES.value,
            "target",
            "=",
        ),
    ),
    (SurfaceDimension.SERVICES.value, "ip"): (
        Pivot(
            "Which web assets resolve to {value}",
            "web assets on {value}",
            SurfaceDimension.WEB_ASSETS.value,
            "ip",
            "=",
        ),
        Pivot(
            "Which findings sit on {value}",
            "findings on {value}",
            SurfaceDimension.VULNERABILITIES.value,
            "ip",
            "=",
        ),
    ),
    (SurfaceDimension.ENDPOINTS.value, "host"): (
        Pivot(
            "Which findings sit on {value}",
            "findings on {value}",
            SurfaceDimension.VULNERABILITIES.value,
            "host",
            "=",
        ),
        Pivot(
            "Which services are open on {value}",
            "services on {value}",
            SurfaceDimension.SERVICES.value,
            "host",
            "=",
        ),
    ),
    (SurfaceDimension.IPS.value, "org"): (
        Pivot(
            "Which web assets sit on {value}",
            "web assets on {value}",
            SurfaceDimension.WEB_ASSETS.value,
            "org",
            "=",
        ),
    ),
}
CVE_PIVOTS: tuple[Pivot, ...] = (
    Pivot(
        "Which web assets carry {value}",
        "web assets carrying {value}",
        SurfaceDimension.WEB_ASSETS.value,
        "cve",
        "=",
    ),
    Pivot(
        "Which findings name {value}",
        "findings naming {value}",
        SurfaceDimension.VULNERABILITIES.value,
        "cve",
        "=",
    ),
    Pivot(
        "Which software versions carry {value}",
        "software CVEs for {value}",
        SurfaceDimension.SOFTWARE.value,
        "cve",
        "=",
    ),
)


# ---------- a thread scoped to one scan ----------

# tools that read runs beside the one a scan thread is scoped to
ACROSS_RUNS: frozenset[str] = frozenset(
    {
        "compare_runs", "cve_exposure", "what_changed", "surface_brief",
        "scan_coverage", "domain_posture", "resolve_target", "list_targets",
        "scan_status",
    }
)  # fmt: skip
# a scope's target clause past this length is counted on its scans alone, with no link
FOLD_CHARS = 1_000
LISTED_SCANS = 40


class ReadKind(StrEnum):
    FIELD = "field"
    FLAG = "flag"
    TEXT = "text"
    OR = "or"
    OPEN = "open"
    CLOSE = "close"
    MORE = "more"


def plain_answer(text: str) -> str:
    """Answer text without its citation marks."""
    return CITATION_MARK.sub("", text)


INSTRUCTION_TEXT = re.compile(
    r"(?i)(ignore (?:all |any )?(?:previous|prior|above) instructions"
    r"|as an ai\b|you are an ai\b|system prompt|ai assistant|language model)"
)
