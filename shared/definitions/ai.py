"""What AI is allowed to do here."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum
from urllib.parse import urlsplit

from shared.enums.instance import AIProvider

MAX_BRIEF_BYTES = 24_000
MAX_OUTPUT_TOKENS = 2_000
REQUEST_TIMEOUT = 120.0
MODEL_LIST_TIMEOUT = 15.0
MODEL_LIST_PAGES = 10
CACHE_VERSION = "1"

MAX_CONNECTION_NAME = 60
MAX_PROVIDER = 32
MAX_MODEL_ID = 80
MAX_BASE_URL = 300
MAX_WORKSPACE_ID = 80
MAX_API_KEY = 400
MAX_TEST_MESSAGE = 500
MAX_PRICE_PER_MTOK = 10_000.0
MAX_CALLS_PAGE = 50
MAX_COST_SOURCE = 16
MAX_CATALOG_ID = 120


class AITask(StrEnum):
    EXECUTIVE_SUMMARY = "executive_summary"
    RISK_NARRATIVE = "risk_narrative"
    REMEDIATION_PLAN = "remediation_plan"
    ISSUE_EXPLAINER = "issue_explainer"
    ATTACK_PATH = "attack_path"
    SURFACE_NARRATIVE = "surface_narrative"
    ASSET_JUDGEMENT = "asset_judgement"
    RULE_SUGGESTION = "rule_suggestion"
    ASK = "ask"
    CONNECTION_TEST = "connection_test"


REPORT_TASKS: tuple[str, ...] = (
    AITask.EXECUTIVE_SUMMARY.value,
    AITask.RISK_NARRATIVE.value,
    AITask.REMEDIATION_PLAN.value,
    AITask.SURFACE_NARRATIVE.value,
    AITask.ATTACK_PATH.value,
)

TASK_OUTPUT_TOKENS: dict[str, int] = {
    AITask.EXECUTIVE_SUMMARY.value: 1400,
    AITask.RISK_NARRATIVE.value: 900,
    AITask.REMEDIATION_PLAN.value: 1200,
    AITask.ISSUE_EXPLAINER.value: 700,
    AITask.ATTACK_PATH.value: 900,
    AITask.SURFACE_NARRATIVE.value: 800,
    AITask.ASSET_JUDGEMENT.value: 2500,
    AITask.RULE_SUGGESTION.value: 900,
    AITask.ASK.value: 4000,
    AITask.CONNECTION_TEST.value: 20,
}


class Effort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


TASK_EFFORT: dict[str, str] = {
    AITask.EXECUTIVE_SUMMARY.value: Effort.MEDIUM.value,
    AITask.RISK_NARRATIVE.value: Effort.LOW.value,
    AITask.REMEDIATION_PLAN.value: Effort.MEDIUM.value,
    AITask.ISSUE_EXPLAINER.value: Effort.LOW.value,
    AITask.ATTACK_PATH.value: Effort.MEDIUM.value,
    AITask.SURFACE_NARRATIVE.value: Effort.LOW.value,
    AITask.ASSET_JUDGEMENT.value: Effort.LOW.value,
    AITask.RULE_SUGGESTION.value: Effort.LOW.value,
    AITask.ASK.value: Effort.MEDIUM.value,
    AITask.CONNECTION_TEST.value: Effort.LOW.value,
}


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    provider: str
    input_per_mtok: float | None = None
    output_per_mtok: float | None = None
    context: int = 200_000
    adaptive_thinking: bool = False
    supports_effort: bool = False
    note: str = ""
    recommended: bool = False
    cache_read_per_mtok: float | None = None
    cache_write_per_mtok: float | None = None


_ANTHROPIC = AIProvider.ANTHROPIC.value
_OPENAI = AIProvider.OPENAI.value
_GOOGLE = AIProvider.GOOGLE.value

MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        "claude-opus-5-5",
        "Claude Opus 5.5",
        _ANTHROPIC,
        4.0,
        20.0,
        1_000_000,
        True,
        True,
        "Default model.",
        recommended=True,
        cache_read_per_mtok=0.2,
        cache_write_per_mtok=5.0,
    ),
    ModelSpec(
        "claude-sonnet-5-5",
        "Claude Sonnet 5.5",
        _ANTHROPIC,
        2.0,
        10.0,
        1_000_000,
        True,
        True,
        "Lower cost.",
        recommended=True,
        cache_read_per_mtok=0.2,
        cache_write_per_mtok=2.5,
    ),
    ModelSpec(
        "claude-haiku-4-5",
        "Claude Haiku 4.5",
        _ANTHROPIC,
        1.0,
        5.0,
        200_000,
        False,
        False,
        "Lowest cost and latency.",
        recommended=True,
        cache_read_per_mtok=0.1,
        cache_write_per_mtok=1.25,
    ),
    ModelSpec(
        "claude-fable-5-1",
        "Claude Fable 5.1",
        _ANTHROPIC,
        10.0,
        50.0,
        1_000_000,
        True,
        True,
        cache_read_per_mtok=0.25,
        cache_write_per_mtok=12.5,
    ),
    ModelSpec(
        "claude-fable-5",
        "Claude Fable 5",
        _ANTHROPIC,
        10.0,
        50.0,
        1_000_000,
        True,
        True,
        cache_read_per_mtok=1.0,
        cache_write_per_mtok=12.5,
    ),
    ModelSpec(
        "claude-opus-5",
        "Claude Opus 5",
        _ANTHROPIC,
        5.0,
        25.0,
        1_000_000,
        True,
        True,
        cache_read_per_mtok=0.5,
        cache_write_per_mtok=6.25,
    ),
    ModelSpec(
        "claude-sonnet-5",
        "Claude Sonnet 5",
        _ANTHROPIC,
        2.0,
        10.0,
        1_000_000,
        True,
        True,
        cache_read_per_mtok=0.2,
        cache_write_per_mtok=2.5,
    ),
    ModelSpec(
        "claude-opus-4-8",
        "Claude Opus 4.8",
        _ANTHROPIC,
        5.0,
        25.0,
        1_000_000,
        True,
        True,
        cache_read_per_mtok=0.5,
        cache_write_per_mtok=6.25,
    ),
    ModelSpec(
        "claude-opus-4-7",
        "Claude Opus 4.7",
        _ANTHROPIC,
        5.0,
        25.0,
        1_000_000,
        True,
        True,
        cache_read_per_mtok=0.5,
        cache_write_per_mtok=6.25,
    ),
    ModelSpec(
        "claude-opus-4-6",
        "Claude Opus 4.6",
        _ANTHROPIC,
        5.0,
        25.0,
        1_000_000,
        True,
        True,
        cache_read_per_mtok=0.5,
        cache_write_per_mtok=6.25,
    ),
    ModelSpec(
        "claude-sonnet-4-6",
        "Claude Sonnet 4.6",
        _ANTHROPIC,
        3.0,
        15.0,
        1_000_000,
        True,
        True,
        cache_read_per_mtok=0.3,
        cache_write_per_mtok=3.75,
    ),
    ModelSpec(
        "gpt-6.1-sol",
        "GPT-6.1 Sol",
        _OPENAI,
        2.0,
        10.0,
        1_050_000,
        note="Default model.",
        recommended=True,
        cache_read_per_mtok=0.1,
        cache_write_per_mtok=2.5,
    ),
    ModelSpec(
        "gpt-6-luna",
        "GPT-6 Luna",
        _OPENAI,
        0.1,
        0.5,
        1_050_000,
        note="Lower cost.",
        recommended=True,
        cache_read_per_mtok=0.01,
        cache_write_per_mtok=0.125,
    ),
    ModelSpec(
        "gpt-6-astra",
        "GPT-6 Astra",
        _OPENAI,
        10.0,
        50.0,
        1_050_000,
        cache_read_per_mtok=1.0,
        cache_write_per_mtok=12.5,
    ),
    ModelSpec(
        "gemini-3.8-flash",
        "Gemini 3.8 Flash",
        _GOOGLE,
        0.75,
        3.75,
        1_048_576,
        note="Default model.",
        recommended=True,
        cache_read_per_mtok=0.075,
    ),
    ModelSpec(
        "gemini-3.5-flash-lite",
        "Gemini 3.5 Flash-Lite",
        _GOOGLE,
        0.3,
        2.5,
        1_048_576,
        note="Lower cost.",
        recommended=True,
        cache_read_per_mtok=0.03,
    ),
)

MODEL_BY_ID: dict[str, ModelSpec] = {m.id: m for m in MODELS}

# dated snapshots, Anthropic and OpenAI spellings
MODEL_SNAPSHOT = re.compile(r"^(?P<alias>.+)-(?:\d{8}|\d{4}-\d{2}-\d{2})$")


def model_alias(model_id: str) -> str:
    """A model id with its snapshot date removed."""
    snapshot = MODEL_SNAPSHOT.match(model_id)
    return snapshot["alias"] if snapshot else model_id


def same_model(a: str, b: str) -> bool:
    return a == b or model_alias(a) == model_alias(b)


def model_spec(model_id: str) -> ModelSpec | None:
    """The curated spec for a model id or its dated snapshot."""
    return MODEL_BY_ID.get(model_id) or MODEL_BY_ID.get(model_alias(model_id))


DEFAULT_MODEL: dict[str, str] = {
    AIProvider.ANTHROPIC.value: "claude-opus-5-5",
    AIProvider.OPENAI.value: "gpt-6.1-sol",
    AIProvider.GOOGLE.value: "gemini-3.8-flash",
    AIProvider.OPENAI_COMPATIBLE.value: "",
}

PROVIDER_LABELS: dict[str, str] = {
    AIProvider.ANTHROPIC.value: "Anthropic",
    AIProvider.OPENAI.value: "OpenAI",
    AIProvider.GOOGLE.value: "Google",
    AIProvider.OPENAI_COMPATIBLE.value: "OpenAI-compatible",
}

PROVIDER_KEY_HINT: dict[str, str] = {
    AIProvider.OPENAI.value: "sk-...",
    AIProvider.ANTHROPIC.value: "sk-ant-...",
    AIProvider.GOOGLE.value: "AIza...",
    AIProvider.OPENAI_COMPATIBLE.value: "Key, or blank for a local server",
}

PROVIDER_HELP: dict[str, str] = {
    AIProvider.OPENAI_COMPATIBLE.value: (
        "Ollama, LM Studio, vLLM, OpenRouter or any server with the OpenAI chat API."
    ),
}

BASE_URL_HINT = "http://ollama:11434/v1 or https://openrouter.ai/api/v1"
BASE_URL_PROVIDERS: frozenset[str] = frozenset({AIProvider.OPENAI_COMPATIBLE.value})
KEY_OPTIONAL_PROVIDERS: frozenset[str] = frozenset({AIProvider.OPENAI_COMPATIBLE.value})
WORKSPACE_PROVIDERS: frozenset[str] = frozenset({AIProvider.ANTHROPIC.value})

# ---------- model listing ----------

OPENAI_CHAT_ID = re.compile(r"^(?:gpt-|chatgpt-|o\d)")
OPENAI_NOT_CHAT: tuple[str, ...] = (
    "embedding",
    "tts",
    "whisper",
    "dall-e",
    "moderation",
    "image",
    "transcribe",
    "realtime",
    "audio",
    "instruct",
)
GOOGLE_GENERATE = "generateContent"


@dataclass(frozen=True)
class AIFeature:
    key: str
    label: str
    help: str
    default: bool = False


AI_FEATURES: tuple[AIFeature, ...] = (
    AIFeature(
        "report_narrative",
        "Report narrative",
        "Executive summary, risk narrative and remediation plan. Sends the target, "
        "counts, check names and the web assets named on attack paths.",
        True,
    ),
    AIFeature(
        "asset_judgement",
        "Asset judgement",
        "Flags exposures after a scan, with a reason. Sends web asset names, status "
        "codes, page titles and technologies.",
        False,
    ),
    AIFeature(
        "rule_suggestions",
        "Rule suggestions",
        "Proposes exposure rules from judgement results, each held for review. Sends "
        "web asset names and judgement reasons.",
        False,
    ),
    AIFeature(
        "ask",
        "Ask",
        "Answers questions about a finding or a web asset in its sheet. Sends the "
        "record, a finding's request and response, and what the read-only tools "
        "return, with secrets masked.",
        True,
    ),
)

DEFAULT_AI_FEATURES: dict[str, bool] = {f.key: f.default for f in AI_FEATURES}

TEST_FEATURE = "connection_test"

TASK_FEATURE: dict[str, str] = {
    AITask.EXECUTIVE_SUMMARY.value: "report_narrative",
    AITask.RISK_NARRATIVE.value: "report_narrative",
    AITask.REMEDIATION_PLAN.value: "report_narrative",
    AITask.ISSUE_EXPLAINER.value: "report_narrative",
    AITask.ATTACK_PATH.value: "report_narrative",
    AITask.SURFACE_NARRATIVE.value: "report_narrative",
    AITask.ASSET_JUDGEMENT.value: "asset_judgement",
    AITask.RULE_SUGGESTION.value: "rule_suggestions",
    AITask.ASK.value: "ask",
    AITask.CONNECTION_TEST.value: TEST_FEATURE,
}

FEATURE_LABELS: dict[str, str] = {
    **{f.key: f.label for f in AI_FEATURES},
    TEST_FEATURE: "Connection tests",
}


def feature_switches(stored: dict | None) -> dict[str, bool]:
    """Every feature switch, stored values over the defaults."""
    saved = stored or {}
    return {
        key: saved[key] if isinstance(saved.get(key), bool) else default
        for key, default in DEFAULT_AI_FEATURES.items()
    }


def model_for(provider: str, requested: str | None) -> str:
    if requested and requested.strip():
        return requested.strip()
    return DEFAULT_MODEL.get(provider, "")


def connection_name(provider: str, base_url: str | None = None) -> str:
    """The name a provider gets when none is given."""
    if provider in BASE_URL_PROVIDERS and base_url:
        host = urlsplit(base_url).hostname
        if host:
            return host[:MAX_CONNECTION_NAME]
    return PROVIDER_LABELS.get(provider, provider)[:MAX_CONNECTION_NAME]


def openai_chat_model(model_id: str) -> bool:
    value = model_id.lower()
    return bool(OPENAI_CHAT_ID.match(value)) and not any(
        token in value for token in OPENAI_NOT_CHAT
    )


# ---------- pricing ----------

PER_MTOK = 1_000_000
# Anthropic 5-minute cache write, over the input rate
CACHE_WRITE_PREMIUM = 1.25
# US-only inference on Claude 4.6 and later, over every rate
US_INFERENCE_PREMIUM = 1.1
US_INFERENCE = "us"
US_PREMIUM_FROM = (4, 6)
REFUSAL = "refusal"
# billed when the model declined before any output
BILLED_REFUSALS: frozenset[str] = frozenset(
    {"bio", "frontier_llm", "reasoning_extraction"}
)
# gateway timeouts: the server behind the gateway may go on generating
GATEWAY_TIMEOUTS: frozenset[int] = frozenset({504, 524})

_CLAUDE_GENERATION = re.compile(
    r"^claude-[a-z]+-(?P<major>\d+)(?:-(?P<minor>\d{1,2}))?$"
)


def us_premium(model: str) -> bool:
    """Whether US-only inference on this Claude model costs more."""
    found = _CLAUDE_GENERATION.match(model_alias(model))
    if found is None:
        return False
    return (int(found["major"]), int(found["minor"] or 0)) >= US_PREMIUM_FROM


class CostSource(StrEnum):
    PROVIDER = "provider"
    LIST = "list"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Rates:
    """Dollars per million tokens."""

    input: float
    output: float
    cache_read: float | None = None
    cache_write: float | None = None

    @property
    def free(self) -> bool:
        return not any((self.input, self.output, self.cache_read, self.cache_write))


Counts = tuple[float, float, float, float]


@dataclass(frozen=True)
class Usage:
    """What one call used: input counts every prompt token, cached or not."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reported_cost: float | None = None
    # false once a round ended without its final usage
    reported: bool = True
    # the counts at the standard rates, set when a round was billed at another multiple
    billable: Counts | None = None

    @property
    def counts(self) -> Counts:
        return (
            self.input_tokens,
            self.output_tokens,
            self.cache_read_tokens,
            self.cache_write_tokens,
        )

    @property
    def charged(self) -> Counts:
        """The counts the rates apply to."""
        return self.counts if self.billable is None else self.billable

    @property
    def used(self) -> bool:
        return any(self.counts)

    def at(self, factor: float) -> Usage:
        """The same tokens billed at a multiple of the standard rates."""
        scaled = tuple(factor * n for n in self.charged)
        return replace(self, billable=None if scaled == self.counts else scaled)

    def __add__(self, other: Usage) -> Usage:
        counts = tuple(a + b for a, b in zip(self.counts, other.counts, strict=True))
        charged = tuple(a + b for a, b in zip(self.charged, other.charged, strict=True))
        return Usage(
            *counts,
            reported_cost=_reported(self, other),
            reported=self.reported and other.reported,
            billable=None if charged == counts else charged,
        )


UNREPORTED = Usage(reported=False)


def _reported(a: Usage, b: Usage) -> float | None:
    if not (a.reported and b.reported):
        return None
    if a.reported_cost is not None and b.reported_cost is not None:
        return a.reported_cost + b.reported_cost
    if a.reported_cost is None and not a.used:
        return b.reported_cost
    if b.reported_cost is None and not b.used:
        return a.reported_cost
    return None


@dataclass(frozen=True)
class Charge:
    usd: float | None = None
    source: str | None = None
    rates: Rates | None = None


def curated_rates(model: str) -> Rates | None:
    spec = model_spec(model)
    if spec is None or spec.input_per_mtok is None or spec.output_per_mtok is None:
        return None
    return Rates(
        spec.input_per_mtok,
        spec.output_per_mtok,
        spec.cache_read_per_mtok,
        spec.cache_write_per_mtok,
    )


def price(usage: Usage, rates: Rates | None, provider: str) -> Charge:
    """Dollars for one call: the provider's own charge, else tokens at the rates, else unknown."""
    if usage.reported_cost is not None:
        return Charge(usage.reported_cost, CostSource.PROVIDER.value)
    if rates is not None and rates.free:
        return Charge(0.0, CostSource.LIST.value, rates)
    if not usage.reported:
        return Charge()
    inputs, outputs, reads, writes = usage.charged
    if not any((inputs, outputs, reads, writes)):
        return Charge(0.0)
    if rates is None:
        return Charge()
    uncached = max(0.0, inputs - reads - writes)
    read_rate = rates.input if rates.cache_read is None else rates.cache_read
    if rates.cache_write is not None:
        write_rate = rates.cache_write
    elif provider == AIProvider.ANTHROPIC.value:
        write_rate = rates.input * CACHE_WRITE_PREMIUM
    else:
        write_rate = rates.input
    usd = (
        uncached * rates.input
        + reads * read_rate
        + writes * write_rate
        + outputs * rates.output
    ) / PER_MTOK
    return Charge(usd, CostSource.LIST.value, rates)
