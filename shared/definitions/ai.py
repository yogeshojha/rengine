"""What AI is allowed to do here."""

from __future__ import annotations

import re
from dataclasses import dataclass
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


MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        "claude-opus-5",
        "Claude Opus 5",
        AIProvider.ANTHROPIC.value,
        5.0,
        25.0,
        1_000_000,
        True,
        True,
        "Default model.",
        recommended=True,
    ),
    ModelSpec(
        "claude-sonnet-5",
        "Claude Sonnet 5",
        AIProvider.ANTHROPIC.value,
        2.0,
        10.0,
        1_000_000,
        True,
        True,
        "Lower cost.",
        recommended=True,
    ),
    ModelSpec(
        "claude-haiku-4-5",
        "Claude Haiku 4.5",
        AIProvider.ANTHROPIC.value,
        1.0,
        5.0,
        200_000,
        False,
        False,
        "Lowest cost and latency.",
        recommended=True,
    ),
    ModelSpec(
        "claude-opus-4-8",
        "Claude Opus 4.8",
        AIProvider.ANTHROPIC.value,
        5.0,
        25.0,
        1_000_000,
        True,
        True,
    ),
    ModelSpec(
        "claude-fable-5-1",
        "Claude Fable 5.1",
        AIProvider.ANTHROPIC.value,
        10.0,
        50.0,
        1_000_000,
        True,
        True,
    ),
    ModelSpec(
        "claude-fable-5",
        "Claude Fable 5",
        AIProvider.ANTHROPIC.value,
        10.0,
        50.0,
        1_000_000,
        True,
        True,
    ),
    ModelSpec(
        "claude-opus-5-5",
        "Claude Opus 5.5",
        AIProvider.ANTHROPIC.value,
        4.0,
        20.0,
        1_000_000,
        True,
        True,
    ),
    ModelSpec(
        "claude-opus-4-7",
        "Claude Opus 4.7",
        AIProvider.ANTHROPIC.value,
        5.0,
        25.0,
        1_000_000,
        True,
        True,
    ),
    ModelSpec(
        "claude-opus-4-6",
        "Claude Opus 4.6",
        AIProvider.ANTHROPIC.value,
        5.0,
        25.0,
        1_000_000,
        True,
        True,
    ),
    ModelSpec(
        "claude-sonnet-5-5",
        "Claude Sonnet 5.5",
        AIProvider.ANTHROPIC.value,
        2.0,
        10.0,
        1_000_000,
        True,
        True,
    ),
    ModelSpec(
        "claude-sonnet-4-6",
        "Claude Sonnet 4.6",
        AIProvider.ANTHROPIC.value,
        3.0,
        15.0,
        1_000_000,
        True,
        True,
    ),
    ModelSpec("gpt-4o", "GPT-4o", AIProvider.OPENAI.value, recommended=True),
    ModelSpec("gpt-4o-mini", "GPT-4o mini", AIProvider.OPENAI.value, recommended=True),
    ModelSpec(
        "gemini-3.8-flash",
        "Gemini 3.8 Flash",
        AIProvider.GOOGLE.value,
        recommended=True,
    ),
    ModelSpec(
        "gemini-3.5-flash-lite",
        "Gemini 3.5 Flash-Lite",
        AIProvider.GOOGLE.value,
        recommended=True,
    ),
)

MODEL_BY_ID: dict[str, ModelSpec] = {m.id: m for m in MODELS}

MODEL_SNAPSHOT = re.compile(r"^(?P<alias>.+)-\d{8}$")


def model_spec(model_id: str) -> ModelSpec | None:
    """The curated spec for a model id or its dated snapshot."""
    spec = MODEL_BY_ID.get(model_id)
    if spec is None and (snapshot := MODEL_SNAPSHOT.match(model_id)):
        spec = MODEL_BY_ID.get(snapshot["alias"])
    return spec


DEFAULT_MODEL: dict[str, str] = {
    AIProvider.ANTHROPIC.value: "claude-opus-5",
    AIProvider.OPENAI.value: "gpt-4o-mini",
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


Rate = tuple[float, float]


def price(
    model: str,
    input_tokens: int,
    output_tokens: int,
    listed: Rate | None = None,
) -> float | None:
    """Dollars for one call: the curated price first, else the listed one."""
    spec = model_spec(model)
    rate = (
        (spec.input_per_mtok, spec.output_per_mtok)
        if spec is not None
        and spec.input_per_mtok is not None
        and spec.output_per_mtok is not None
        else listed
    )
    if rate is None:
        return None
    return (input_tokens * rate[0] + output_tokens * rate[1]) / 1_000_000
