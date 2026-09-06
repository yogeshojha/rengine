from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, choice, flag, paragraph, text
from shared.definitions.reports import SectionGroup


class CustomTextConfig(SectionConfig):
    heading: str = text("Notes", title="Heading")
    body: str = paragraph(
        "",
        title="Body",
        description="Markdown. Headings, lists, tables and code all render.",
    )
    style: str = choice(
        "plain",
        title="Presentation",
        options={
            "plain": "Plain text",
            "callout": "Callout",
            "warning": "Warning callout",
            "quiet": "Quiet note",
        },
    )
    new_page: bool = flag(True, title="Start on a new page")


class CustomTextSection(Section):
    name = "custom_text"
    title = "Custom text"
    description = "Anything you want to say, in Markdown. Add as many as you need."
    group = SectionGroup.SUMMARY.value
    order = 60
    repeatable = True
    default_enabled = False
    config_model = CustomTextConfig

    def build(self, ctx: RenderContext, cfg: CustomTextConfig) -> dict | None:
        del ctx
        if not cfg.body.strip():
            return None
        kind = {"callout": "", "warning": "warn", "quiet": "quiet"}.get(cfg.style)
        return {
            "title": cfg.heading,
            "body": cfg.body,
            "callout": cfg.style != "plain",
            "kind": kind,
        }
