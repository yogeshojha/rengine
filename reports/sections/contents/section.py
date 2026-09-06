from __future__ import annotations

from reports.base import RenderContext, Section
from reports.config import SectionConfig, flag, text
from shared.definitions.reports import SectionGroup, SectionRole


class ContentsConfig(SectionConfig):
    heading: str = text("Contents", title="Heading")
    show_subsections: bool = flag(
        False,
        title="List findings too",
        description="Off by default: the findings chapter is already their index.",
    )


class ContentsSection(Section):
    name = "contents"
    title = "Contents"
    description = "A table of contents with real page numbers, resolved at layout time."
    group = SectionGroup.FRONT_MATTER.value
    order = 30
    role = SectionRole.FURNITURE.value
    in_toc = False
    config_model = ContentsConfig

    def build(self, ctx: RenderContext, cfg: ContentsConfig) -> dict:
        del ctx
        return {"bare": True, "heading": cfg.heading, "show_subs": cfg.show_subsections}
