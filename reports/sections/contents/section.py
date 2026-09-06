from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, text
from shared.definitions.reports import SectionGroup, SectionRole


class ContentsConfig(SectionConfig):
    heading: str = text("Contents", title="Heading")
    show_subsections: bool = flag(
        False,
        title="List findings in the contents",
        description="Off by default. The findings chapter already indexes them.",
    )


class ContentsSection(Section):
    name = "contents"
    title = "Contents"
    description = "A table of contents with real page numbers."
    group = SectionGroup.FRONT_MATTER.value
    order = 30
    role = SectionRole.FURNITURE.value
    in_toc = False
    config_model = ContentsConfig

    def build(self, ctx: RenderContext, cfg: ContentsConfig) -> dict:
        del ctx
        return {"bare": True, "heading": cfg.heading, "show_subs": cfg.show_subsections}
