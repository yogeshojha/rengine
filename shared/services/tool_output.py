"""What a tool result may carry to a model provider."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from shared.definitions.ask import SECRET_TAGS
from shared.definitions.compare import WATCHED_FIELDS
from shared.definitions.surface import SurfaceDimension
from shared.services.issue_tracking.body import mask_secrets
from shared.services.scan_resolve import MASK, redact_credentials

ROW_TOOLS = frozenset({"query_assets", "compare_runs"})
VALUE_GROUP = ("group_assets", "value")
EXPLAIN_TOOL = "explain_finding"
COMPARE_TOOL = "compare_runs"
EXTRACTED_FIELD = "extracted_results"


def hides_values(template_id: str, tags: Iterable[str]) -> bool:
    """Whether a check's extracted values are credentials."""
    words = {t.lower() for t in tags} | set(template_id.lower().split("-"))
    return bool(words & SECRET_TAGS)


def reads_secret_values(name: str, args: dict) -> bool:
    """Whether a call would return the secrets dimension's raw values."""
    if args.get("dimension") != SurfaceDimension.SECRETS.value:
        return False
    return name in ROW_TOOLS or (name, args.get("group_by")) == VALUE_GROUP


def scrub(value: Any) -> Any:
    """Mask every string leaf of a tool payload."""
    if isinstance(value, str):
        return mask_secrets(redact_credentials(value))
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


def _extracted_label() -> str:
    fields = WATCHED_FIELDS[SurfaceDimension.VULNERABILITIES.value]
    return next(f.label for f in fields if f.name == EXTRACTED_FIELD)


def hide_extracted(name: str, data: Any) -> Any:
    """Replace extracted values a credential check found, and every compared one."""
    if not isinstance(data, dict):
        return data
    if name == EXPLAIN_TOOL:
        check = data.get("check") or {}
        evidence = data.get("evidence") or {}
        shown = evidence.get("extracted")
        if shown and hides_values(
            str(check.get("template_id") or ""), check.get("tags") or []
        ):
            evidence["extracted"] = [MASK for _ in shown]
    elif name == COMPARE_TOOL:
        extracted = _extracted_label()
        for change in data.get("changes") or []:
            for field in change.get("fields") or []:
                if field.get("field") != extracted:
                    continue
                for side in ("was", "now"):
                    if field.get(side):
                        field[side] = MASK
    return data


def guarded(name: str, data: Any) -> Any:
    """A tool's data with string leaves masked and credential extracts replaced."""
    return hide_extracted(name, scrub(data))
