"""Ask: a read-only conversation on a finding or a web asset."""

from __future__ import annotations

import re
from enum import StrEnum

from shared.definitions.surface import SurfaceDimension

ASK_CLIENT = "ask"
MAX_THREADS_PER_FINDING = 12
MAX_TITLE = 80
MAX_QUESTION_CHARS = 4_000
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

STARTERS: dict[str, tuple[str, ...]] = {
    SurfaceDimension.VULNERABILITIES.value: (
        "What is the impact of this finding?",
        "Could this be a false positive?",
        "How do I reproduce it?",
        "What is the fix for this version?",
    ),
    SurfaceDimension.WEB_ASSETS.value: (
        "What is this web asset?",
        "Is this an admin or internal interface?",
        "What should I test by hand first?",
        "Which findings and exposures sit on it?",
    ),
}
ASK_DIMENSIONS: tuple[str, ...] = tuple(STARTERS)

CITATION = re.compile(r"( ?)\[(F|T|R)(\d{1,3})\]")
CITATION_MARK = re.compile(r" ?\[\[(\d{1,2})\]\]")


def plain_answer(text: str) -> str:
    """Answer text without its citation marks."""
    return CITATION_MARK.sub("", text)


INSTRUCTION_TEXT = re.compile(
    r"(?i)(ignore (?:all |any )?(?:previous|prior|above) instructions"
    r"|as an ai\b|you are an ai\b|system prompt|ai assistant|language model)"
)
