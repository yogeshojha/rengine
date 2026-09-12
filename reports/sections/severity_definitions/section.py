from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag
from shared.definitions.reports import SectionGroup, SectionRole
from shared.definitions.vulnerabilities import (
    EPSS_HIGH,
    SEVERITY_HELP,
    SEVERITY_LABELS,
    SEVERITY_ORDER,
    Severity,
)

_GLOSSARY = (
    (
        "CVSS",
        "A severity score from 0 to 10. It does not measure exploitation.",
    ),
    (
        "EPSS",
        f"The modelled probability of exploitation in the next 30 days. Above {int(EPSS_HIGH * 100)}% is treated as likely.",
    ),
    (
        "KEV",
        "The CISA Known Exploited Vulnerabilities catalogue. Listed weaknesses have confirmed exploitation.",
    ),
    (
        "CWE",
        "The weakness class. Control mapping is derived from it.",
    ),
    (
        "New",
        "Not present in the previous run of this target. A first run reports nothing as new.",
    ),
    (
        "Suppressed",
        "Marked as a false positive or an accepted risk. Excluded from this and later runs.",
    ),
)


class SeverityDefinitionsConfig(SectionConfig):
    show_glossary: bool = flag(True, title="Show glossary")
    show_scoring: bool = flag(True, title="Show ranking method")


class SeverityDefinitionsSection(Section):
    name = "severity_definitions"
    title = "Definitions"
    description = "Severity definitions and the ranking method."
    page_break = "flow"
    group = SectionGroup.APPENDIX.value
    order = 30
    role = SectionRole.FURNITURE.value
    config_model = SeverityDefinitionsConfig

    def build(self, ctx: RenderContext, cfg: SeverityDefinitionsConfig) -> dict:
        del ctx
        return {
            "severities": [
                {"key": key, "label": SEVERITY_LABELS[key], "help": SEVERITY_HELP[key]}
                for key in SEVERITY_ORDER
                if key != Severity.UNKNOWN.value
            ],
            "glossary": _GLOSSARY if cfg.show_glossary else (),
            "show_scoring": cfg.show_scoring,
        }
