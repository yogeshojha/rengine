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
        "A score from 0 to 10 describing how severe a weakness is in the abstract. It says nothing about whether this weakness is being exploited.",
    ),
    (
        "EPSS",
        f"The modelled probability that a weakness will be exploited in the next 30 days. Above {int(EPSS_HIGH * 100)}% is treated as likely here.",
    ),
    (
        "KEV",
        "The Known Exploited Vulnerabilities catalogue. Membership means exploitation has been confirmed in the wild.",
    ),
    (
        "CWE",
        "The weakness class, which is what the control mapping in this report is derived from.",
    ),
    (
        "New",
        "Not present in the previous run of this target. A first run reports nothing as new.",
    ),
    (
        "Suppressed",
        "Reviewed and marked as a false positive or an accepted risk. Suppressed findings stay hidden on later runs.",
    ),
)


class SeverityDefinitionsConfig(SectionConfig):
    show_glossary: bool = flag(True, title="Show the glossary")
    show_scoring: bool = flag(True, title="Explain how findings are ranked")


class SeverityDefinitionsSection(Section):
    name = "severity_definitions"
    title = "How to read this report"
    description = "What each severity means, and how findings were ranked."
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
