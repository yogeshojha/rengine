from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, paragraph
from shared.definitions.reports import SectionGroup, SectionRole

_DEFAULT_CONFIDENTIALITY = (
    "This document contains information about security weaknesses in systems operated by "
    "the client named on the cover. Distribute it only to the people listed below."
)


class DocumentControlConfig(SectionConfig):
    show_distribution: bool = flag(True, title="Show distribution list")
    show_revisions: bool = flag(True, title="Show revision history")
    show_confidentiality: bool = flag(True, title="Show confidentiality statement")
    show_disclaimer: bool = flag(True, title="Show disclaimer")
    confidentiality: str = paragraph(
        _DEFAULT_CONFIDENTIALITY,
        title="Confidentiality statement",
        description="Used when the branding field is empty.",
    )


class DocumentControlSection(Section):
    name = "document_control"
    title = "Document control"
    description = "Version, distribution, revision history and handling instructions."
    group = SectionGroup.FRONT_MATTER.value
    order = 20
    role = SectionRole.FURNITURE.value
    default_enabled = False
    config_model = DocumentControlConfig

    def build(self, ctx: RenderContext, cfg: DocumentControlConfig) -> dict:
        branding = ctx.branding
        facts = [
            ("Document", ctx.spec.title),
            ("Reference", branding.document_id),
            ("Version", branding.version),
            ("Classification", branding.classification),
            ("Client", branding.client_name),
            ("Author", branding.author or branding.prepared_by),
            ("Issued", ctx.now.strftime("%d %B %Y")),
            ("Subject", ctx.data.subject),
        ]
        return {
            "facts": [(label, value) for label, value in facts if value],
            "distribution": branding.distribution if cfg.show_distribution else [],
            "revisions": branding.revisions if cfg.show_revisions else [],
            "confidentiality": (
                branding.confidentiality_statement or cfg.confidentiality
            )
            if cfg.show_confidentiality
            else "",
            "disclaimer": branding.disclaimer if cfg.show_disclaimer else "",
        }
