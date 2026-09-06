"""Shipped documents. A preset is a section list plus a look, exactly like a saved template."""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.definitions.compliance import DEFAULT_FRAMEWORKS
from shared.definitions.reports import (
    Audience,
    Density,
    Depth,
    ReportFormat,
    ReportScope,
    SectionEntry,
)


@dataclass(frozen=True)
class Preset:
    slug: str
    name: str
    description: str
    scope: str
    theme: str
    sections: tuple[tuple[str, dict], ...]
    formats: tuple[str, ...] = (ReportFormat.PDF.value,)
    audience: str = Audience.MIXED.value
    depth: str = Depth.STANDARD.value
    density: str = Density.NORMAL.value
    title: str = ""
    subtitle: str = ""
    default: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)

    def entries(self) -> list[SectionEntry]:
        return [
            SectionEntry(section=name, config=dict(config))
            for name, config in self.sections
        ]


PRESETS: tuple[Preset, ...] = (
    Preset(
        slug="vapt",
        name="Penetration test report",
        description="The full deliverable: scope, methodology, findings with evidence, remediation and appendices.",
        scope=ReportScope.SCAN.value,
        theme="consulting",
        title="Security Assessment Report",
        subtitle="Unauthenticated external assessment",
        audience=Audience.MIXED.value,
        depth=Depth.DETAILED.value,
        default=True,
        tags=("pentest", "client"),
        sections=(
            ("cover", {}),
            ("document_control", {}),
            ("contents", {}),
            ("executive_summary", {}),
            ("risk_summary", {}),
            ("attack_paths", {}),
            ("findings_detail", {"max_issues": 100, "show_evidence": True}),
            ("remediation_plan", {}),
            ("methodology", {}),
            ("coverage", {}),
            ("severity_definitions", {}),
            ("signoff", {}),
        ),
    ),
    Preset(
        slug="executive",
        name="Executive brief",
        description="Four pages for a decision maker: posture, the chains that matter and what to do first.",
        scope=ReportScope.SCAN.value,
        theme="editorial",
        title="Security Posture Brief",
        audience=Audience.EXECUTIVE.value,
        depth=Depth.BRIEF.value,
        density=Density.RELAXED.value,
        tags=("board", "summary"),
        sections=(
            ("cover", {}),
            ("executive_summary", {"show_severity": True, "show_deductions": True}),
            ("attack_paths", {"top": 3, "show_evidence": False}),
            ("changes", {"list_added": False, "list_gone": False}),
            ("remediation_plan", {"top": 6, "show_owner": True}),
            ("signoff", {}),
        ),
    ),
    Preset(
        slug="attack_surface",
        name="Attack surface report",
        description="What exists and how it is hosted. For a recon run with no vulnerability scanning.",
        scope=ReportScope.SCAN.value,
        theme="midnight",
        title="External Attack Surface Report",
        tags=("recon", "asm"),
        sections=(
            ("cover", {}),
            ("contents", {}),
            ("executive_summary", {"show_severity": False}),
            ("surface_overview", {}),
            ("hosting", {}),
            ("web_assets", {"max_rows": 120}),
            ("services", {}),
            ("ip_addresses", {}),
            ("certificates", {}),
            ("endpoints", {}),
            ("scope_recommendations", {}),
            ("methodology", {}),
            ("coverage", {}),
        ),
    ),
    Preset(
        slug="change",
        name="Change report",
        description="What appeared, what went away and what is newly at risk since the previous run.",
        scope=ReportScope.SCAN.value,
        theme="blueprint",
        title="Attack Surface Change Report",
        depth=Depth.BRIEF.value,
        density=Density.COMPACT.value,
        tags=("delta", "monitoring"),
        sections=(
            ("cover", {}),
            ("executive_summary", {"show_kpis": True, "show_deductions": False}),
            ("changes", {"max_items": 40}),
            ("surface_overview", {"show_narrative": False}),
            ("attack_paths", {"top": 4}),
            ("coverage", {}),
        ),
    ),
    Preset(
        slug="technical",
        name="Full technical report",
        description="Everything the run produced, including full inventories and per-finding evidence.",
        scope=ReportScope.SCAN.value,
        theme="terminal",
        title="Technical Assessment Report",
        audience=Audience.TECHNICAL.value,
        depth=Depth.DETAILED.value,
        density=Density.COMPACT.value,
        formats=(
            ReportFormat.PDF.value,
            ReportFormat.HTML.value,
            ReportFormat.JSON.value,
        ),
        tags=("engineering",),
        sections=(
            ("cover", {}),
            ("contents", {}),
            ("executive_summary", {}),
            ("surface_overview", {}),
            ("risk_summary", {"top": 25}),
            ("attack_paths", {}),
            (
                "findings_detail",
                {
                    "max_issues": 200,
                    "max_assets": 50,
                    "show_evidence": True,
                    "show_curl": True,
                },
            ),
            ("remediation_plan", {"top": 30}),
            ("hosting", {}),
            ("web_assets", {"max_rows": 200, "only_live": False}),
            ("services", {"max_rows": 200}),
            ("ip_addresses", {"max_rows": 200}),
            ("endpoints", {"max_rows": 200}),
            ("certificates", {"problems_only": False}),
            ("dns_records", {}),
            ("whois", {}),
            ("methodology", {}),
            ("coverage", {}),
            ("appendix_assets", {"include_services": True}),
            ("severity_definitions", {}),
        ),
    ),
    Preset(
        slug="compliance",
        name="Compliance evidence pack",
        description="Findings mapped to OWASP, PCI DSS, ISO 27001 and NIST CSF for an audit file.",
        scope=ReportScope.SCAN.value,
        theme="consulting",
        title="Control Evidence Report",
        tags=("audit", "compliance"),
        sections=(
            ("cover", {}),
            ("document_control", {}),
            ("contents", {}),
            ("executive_summary", {}),
            (
                "compliance",
                {
                    "frameworks": [
                        *DEFAULT_FRAMEWORKS,
                        "pci_dss",
                        "iso_27001",
                        "nist_csf",
                    ]
                },
            ),
            ("risk_summary", {}),
            (
                "findings_detail",
                {"max_issues": 80, "show_evidence": False, "show_controls": True},
            ),
            ("remediation_plan", {}),
            ("methodology", {}),
            ("coverage", {}),
            ("severity_definitions", {}),
        ),
    ),
    Preset(
        slug="inventory",
        name="Asset inventory",
        description="The tables only. Every host, address, service and endpoint the run holds.",
        scope=ReportScope.TARGET.value,
        theme="blueprint",
        title="Asset Inventory",
        density=Density.COMPACT.value,
        formats=(ReportFormat.PDF.value, ReportFormat.JSON.value),
        tags=("inventory",),
        sections=(
            ("cover", {}),
            ("contents", {}),
            ("surface_overview", {}),
            ("web_assets", {"max_rows": 500, "only_live": False}),
            ("ip_addresses", {"max_rows": 500}),
            ("services", {"max_rows": 500}),
            ("endpoints", {"max_rows": 300, "notable_only": False}),
            ("appendix_assets", {"include_services": True}),
            ("coverage", {}),
        ),
    ),
)

PRESET_BY_SLUG: dict[str, Preset] = {p.slug: p for p in PRESETS}
DEFAULT_PRESET = next((p.slug for p in PRESETS if p.default), PRESETS[0].slug)
