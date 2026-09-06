from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, paragraph, text
from shared.definitions.reports import SectionGroup


class SignoffConfig(SectionConfig):
    body: str = paragraph(
        "",
        title="Closing note",
        description="Markdown printed above the contact block.",
    )
    show_contact: bool = flag(True, title="Show contact details")
    show_signature: bool = flag(False, title="Add signature lines")
    signature_label: str = text("Reviewed by", title="Signature label")


class SignoffSection(Section):
    name = "signoff"
    title = "Contact"
    description = (
        "The closing page: who to contact and, if you need them, signature lines."
    )
    page_break = "flow"
    group = SectionGroup.APPENDIX.value
    default_enabled = False
    config_model = SignoffConfig

    def build(self, ctx: RenderContext, cfg: SignoffConfig) -> dict:
        branding = ctx.branding
        contact = [
            ("Prepared by", branding.prepared_by or branding.company_name),
            ("Author", branding.author),
            ("Email", branding.contact_email),
            ("Web", branding.contact_url),
        ]
        return {
            "body": cfg.body,
            "contact": [(k, v) for k, v in contact if v] if cfg.show_contact else [],
            "signature": cfg.show_signature,
            "signature_label": cfg.signature_label,
        }
