"""A section is a unit of the document: what it needs, what it configures, what it renders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

from reports.config import SectionConfig
from shared.definitions.reports import ReportSpec, SectionGroup

if TYPE_CHECKING:
    from reports.analysis.brief import ReportBrief
    from reports.data.source import ReportSource
    from reports.narrate.base import Narrator
    from shared.definitions.report_theme import ThemeTokens


@dataclass
class Counters:
    figure: int = 0
    table: int = 0

    def next_figure(self) -> int:
        self.figure += 1
        return self.figure

    def next_table(self) -> int:
        self.table += 1
        return self.table


@dataclass
class RenderContext:
    spec: ReportSpec
    theme: ThemeTokens
    data: ReportSource
    brief: ReportBrief
    narrator: Narrator
    now: datetime
    counters: Counters = field(default_factory=Counters)
    preview: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def style(self):
        return self.spec.style

    @property
    def branding(self):
        return self.spec.branding

    @property
    def palette(self) -> dict[str, str]:
        colour = self.theme.color
        return {
            "ink": colour.ink,
            "ink_soft": colour.ink_soft,
            "ink_faint": colour.ink_faint,
            "surface": colour.surface,
            "accent": colour.accent,
            "accent_ink": colour.accent_ink,
            "rule": colour.rule,
        }

    def sev(self, severity: str | None) -> str:
        table = self.theme.color.severity
        return table.get((severity or "unknown").lower(), self.theme.color.ink_faint)

    def hue(self, index: int) -> str:
        scale = self.theme.color.chart or [self.theme.color.accent]
        return scale[index % len(scale)]

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)


@dataclass
class SectionOutput:
    """What one section contributes to the document."""

    html: str
    title: str = ""
    in_toc: bool = True
    anchor: str = ""
    page_break: str = "auto"
    bookmarks: list[tuple[str, str]] = field(default_factory=list)


class Section(ABC):
    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str] = ""
    group: ClassVar[str] = SectionGroup.SUMMARY.value
    requires: ClassVar[frozenset[str]] = frozenset()
    repeatable: ClassVar[bool] = False
    default_enabled: ClassVar[bool] = True
    in_toc: ClassVar[bool] = True
    page_break: ClassVar[str] = "auto"
    template: ClassVar[str] = ""
    config_model: ClassVar[type[SectionConfig]] = SectionConfig

    @classmethod
    def template_name(cls) -> str:
        return cls.template or f"{cls.name}/section.html"

    @classmethod
    def defaults(cls) -> dict:
        return cls.config_model().model_dump()

    @classmethod
    def schema(cls) -> dict:
        return cls.config_model.model_json_schema()

    def available(self, ctx: RenderContext) -> bool:
        return not self.requires or bool(self.requires & ctx.data.covered_dimensions)

    @abstractmethod
    def build(self, ctx: RenderContext, cfg: SectionConfig) -> dict | None:
        """Template variables, or None when the section has nothing to say."""
