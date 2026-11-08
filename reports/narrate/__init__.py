from reports.narrate.ai import AiNarrator
from reports.narrate.base import Narrator
from reports.narrate.deterministic import PlainNarrator
from shared.definitions.ai import AIFeatureKey
from shared.definitions.reports import NarrativeOptions
from shared.services.ai.config import AIConfig

__all__ = ["AiNarrator", "Narrator", "PlainNarrator", "build_narrator"]


def build_narrator(
    session, cfg: AIConfig | None, options: NarrativeOptions
) -> Narrator:
    """AI writes only when the instance allows it and the report asked for it."""
    if (
        options.ai_enabled
        and cfg is not None
        and cfg.allows(AIFeatureKey.REPORT_NARRATIVE.value)
    ):
        return AiNarrator(session, cfg, options)
    return PlainNarrator()
