"""What AI is allowed to do here."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.enums.instance import AIProvider

MAX_BRIEF_BYTES = 24_000
MAX_OUTPUT_TOKENS = 2_000
REQUEST_TIMEOUT = 120.0
CACHE_VERSION = "1"


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
    ModelSpec("gpt-4o", "GPT-4o", AIProvider.OPENAI.value),
    ModelSpec("gpt-4o-mini", "GPT-4o mini", AIProvider.OPENAI.value),
    ModelSpec("gemini-3.8-flash", "Gemini 3.8 Flash", AIProvider.GOOGLE.value),
    ModelSpec(
        "gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite", AIProvider.GOOGLE.value
    ),
)

MODEL_BY_ID: dict[str, ModelSpec] = {m.id: m for m in MODELS}

DEFAULT_MODEL: dict[str, str] = {
    AIProvider.ANTHROPIC.value: "claude-opus-5",
    AIProvider.OPENAI.value: "gpt-4o-mini",
    AIProvider.GOOGLE.value: "gemini-3.8-flash",
    AIProvider.OPENAI_COMPATIBLE.value: "",
}

FAST_MODEL: dict[str, str] = {
    AIProvider.ANTHROPIC.value: "claude-haiku-4-5",
    AIProvider.OPENAI.value: "gpt-4o-mini",
    AIProvider.GOOGLE.value: "gemini-3.5-flash-lite",
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


def model_for(provider: str, requested: str | None, *, fast: bool = False) -> str:
    if requested and requested.strip():
        return requested.strip()
    table = FAST_MODEL if fast else DEFAULT_MODEL
    if provider in table:
        return table[provider]
    return DEFAULT_MODEL[AIProvider.ANTHROPIC.value]


def price(model: str, input_tokens: int, output_tokens: int) -> float | None:
    spec = MODEL_BY_ID.get(model)
    if spec is None or spec.input_per_mtok is None or spec.output_per_mtok is None:
        return None
    return (
        input_tokens * spec.input_per_mtok + output_tokens * spec.output_per_mtok
    ) / 1_000_000
