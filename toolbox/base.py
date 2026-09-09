"""Tool declaration and the result vocabulary a tool answers in."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict

from shared.definitions.toolbox import (
    Block,
    BlockKind,
    Cell,
    Fact,
    Pivot,
    Tag,
    Tone,
    ToolExecution,
    ToolGroup,
)


class ToolError(Exception):
    """A failure whose message is shown to the operator verbatim."""


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


@dataclass
class ToolContext:
    session: Any
    user_id: uuid.UUID
    project_id: uuid.UUID | None = None


@dataclass
class ToolOutcome:
    summary: str
    blocks: list[Block] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    pivot: Pivot | None = None
    raw: dict | None = None


class Tool(ABC):
    name: ClassVar[str]
    title: ClassVar[str]
    description: ClassVar[str]
    group: ClassVar[str] = ToolGroup.LOOKUP.value
    icon: ClassVar[str] = "search"
    execution: ClassVar[str] = ToolExecution.INLINE.value
    touches_target: ClassVar[bool] = False
    placeholder: ClassVar[str] = ""
    examples: ClassVar[tuple[str, ...]] = ()
    Input: ClassVar[type[ToolInput]]

    @classmethod
    def schema(cls) -> dict:
        return cls.Input.model_json_schema()

    @classmethod
    def label_for(cls, args: ToolInput) -> str:
        """The value that names the run in history: the first string field."""
        for value in args.model_dump().values():
            if isinstance(value, str) and value.strip():
                return value.strip()
        return cls.title

    @abstractmethod
    def run(self, ctx: ToolContext, args: Any) -> ToolOutcome: ...


def facts(*rows: Fact, title: str | None = None, empty: str | None = None) -> Block:
    return Block(
        kind=BlockKind.FACTS.value,
        title=title,
        facts=[r for r in rows if r is not None],
        empty=empty,
    )


def fact(
    label: str,
    value: Any,
    *,
    tone: str = Tone.NEUTRAL.value,
    note: str | None = None,
    href: str | None = None,
    mono: bool = False,
) -> Fact | None:
    """A row, or None when the value is blank."""
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    return Fact(label=label, value=text, tone=tone, note=note, href=href, mono=mono)


def table(
    columns: list[str],
    rows: list[list[Cell]],
    *,
    title: str | None = None,
    empty: str | None = None,
    total: int | None = None,
) -> Block:
    return Block(
        kind=BlockKind.TABLE.value,
        title=title,
        columns=columns,
        rows=rows,
        empty=empty,
        total=total,
    )


def cell(
    value: Any,
    *,
    tone: str = Tone.NEUTRAL.value,
    note: str | None = None,
    href: str | None = None,
    mono: bool = False,
    icon: str | None = None,
) -> Cell:
    return Cell(
        value="" if value is None else str(value),
        tone=tone,
        note=note,
        href=href,
        mono=mono,
        icon=icon,
    )


def tags(
    values: list[Tag], *, title: str | None = None, empty: str | None = None
) -> Block:
    return Block(kind=BlockKind.TAGS.value, title=title, tags=values, empty=empty)


def tag(
    value: str,
    *,
    tone: str = Tone.NEUTRAL.value,
    icon: str | None = None,
    href: str | None = None,
    note: str | None = None,
) -> Tag:
    return Tag(value=value, tone=tone, icon=icon, href=href, note=note)


def code(text: str, *, lang: str | None = None, title: str | None = None) -> Block:
    return Block(kind=BlockKind.CODE.value, title=title, text=text, lang=lang)


def note(text: str, *, tone: str = Tone.INFO.value) -> Block:
    return Block(kind=BlockKind.NOTE.value, text=text, tone=tone)
