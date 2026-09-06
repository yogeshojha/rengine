"""What AI is allowed to do here, which models do it, and what it costs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared.enums.instance import AIProvider

MAX_BRIEF_BYTES = 24_000
MAX_CALLS_PER_REPORT = 40
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


AI_TASK_LABELS: dict[str, str] = {
    AITask.EXECUTIVE_SUMMARY.value: "Executive summary",
    AITask.RISK_NARRATIVE.value: "Risk narrative",
    AITask.REMEDIATION_PLAN.value: "Remediation plan",
    AITask.ISSUE_EXPLAINER.value: "Finding explanations",
    AITask.ATTACK_PATH.value: "Attack path narrative",
    AITask.SURFACE_NARRATIVE.value: "Attack surface narrative",
}

# tasks that run once per report against the brief, versus once per distinct check
REPORT_TASKS: tuple[str, ...] = (
    AITask.EXECUTIVE_SUMMARY.value,
    AITask.RISK_NARRATIVE.value,
    AITask.REMEDIATION_PLAN.value,
    AITask.SURFACE_NARRATIVE.value,
    AITask.ATTACK_PATH.value,
)

# an explainer depends only on the check, so it is cached across every report and target
GLOBAL_CACHE_TASKS: tuple[str, ...] = (AITask.ISSUE_EXPLAINER.value,)

TASK_OUTPUT_TOKENS: dict[str, int] = {
    AITask.EXECUTIVE_SUMMARY.value: 1400,
    AITask.RISK_NARRATIVE.value: 900,
    AITask.REMEDIATION_PLAN.value: 1200,
    AITask.ISSUE_EXPLAINER.value: 700,
    AITask.ATTACK_PATH.value: 900,
    AITask.SURFACE_NARRATIVE.value: 800,
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


# priced models are Anthropic's published rates; other providers are listed without a price
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
        "Best writing. The default.",
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
        "Cheaper, still strong.",
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
        "Fastest and cheapest.",
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
    ModelSpec("gemini-1.5-pro", "Gemini 1.5 Pro", AIProvider.GOOGLE.value),
    ModelSpec("gemini-1.5-flash", "Gemini 1.5 Flash", AIProvider.GOOGLE.value),
)

MODEL_BY_ID: dict[str, ModelSpec] = {m.id: m for m in MODELS}

DEFAULT_MODEL: dict[str, str] = {
    AIProvider.ANTHROPIC.value: "claude-opus-5",
    AIProvider.OPENAI.value: "gpt-4o-mini",
    AIProvider.AZURE_OPENAI.value: "gpt-4o-mini",
    AIProvider.GOOGLE.value: "gemini-1.5-flash",
}

# the cheap tier used for per-check explainers, which are cached forever once written
FAST_MODEL: dict[str, str] = {
    AIProvider.ANTHROPIC.value: "claude-haiku-4-5",
    AIProvider.OPENAI.value: "gpt-4o-mini",
    AIProvider.AZURE_OPENAI.value: "gpt-4o-mini",
    AIProvider.GOOGLE.value: "gemini-1.5-flash",
}

PROVIDER_LABELS: dict[str, str] = {
    AIProvider.OPENAI.value: "OpenAI",
    AIProvider.ANTHROPIC.value: "Anthropic",
    AIProvider.AZURE_OPENAI.value: "Azure OpenAI",
    AIProvider.GOOGLE.value: "Google",
}

PROVIDER_KEY_HINT: dict[str, str] = {
    AIProvider.OPENAI.value: "sk-...",
    AIProvider.ANTHROPIC.value: "sk-ant-...",
    AIProvider.AZURE_OPENAI.value: "Azure resource key",
    AIProvider.GOOGLE.value: "AIza...",
}


@dataclass(frozen=True)
class AIFeature:
    key: str
    label: str
    help: str
    default: bool = False


# what the instance allows AI to be used for; a report still opts in per run
AI_FEATURES: tuple[AIFeature, ...] = (
    AIFeature(
        "report_narrative",
        "Report narrative",
        "Writes the executive summary, risk narrative and remediation plan from the computed brief.",
        True,
    ),
    AIFeature(
        "report_findings",
        "Finding explanations",
        "Explains what a check means for this estate. Cached per check, so it is written once.",
        False,
    ),
    AIFeature(
        "attack_paths",
        "Attack path narrative",
        "Describes how observed weaknesses chain together.",
        False,
    ),
)

AI_FEATURE_KEYS: tuple[str, ...] = tuple(f.key for f in AI_FEATURES)
DEFAULT_AI_FEATURES: dict[str, bool] = {f.key: f.default for f in AI_FEATURES}


def model_for(provider: str, requested: str | None, *, fast: bool = False) -> str:
    if requested and requested.strip():
        return requested.strip()
    table = FAST_MODEL if fast else DEFAULT_MODEL
    return table.get(provider, DEFAULT_MODEL[AIProvider.ANTHROPIC.value])


def price(model: str, input_tokens: int, output_tokens: int) -> float | None:
    spec = MODEL_BY_ID.get(model)
    if spec is None or spec.input_per_mtok is None or spec.output_per_mtok is None:
        return None
    return (
        input_tokens * spec.input_per_mtok + output_tokens * spec.output_per_mtok
    ) / 1_000_000
