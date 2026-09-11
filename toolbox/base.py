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
    Identity,
    IdentityKind,
    Lookup,
    Mark,
    Meter,
    Metric,
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
    order: ClassVar[int] = 50
    value_field: ClassVar[str] = ""
    placeholder: ClassVar[str] = ""
    examples: ClassVar[tuple[str, ...]] = ()
    Input: ClassVar[type[ToolInput]]

    @classmethod
    def schema(cls) -> dict:
        return cls.Input.model_json_schema()

    @classmethod
    def payload_for(cls, value: str) -> dict:
        return {cls.value_field: value}

    @classmethod
    def label_for(cls, args: ToolInput) -> str:
        value = args.model_dump().get(cls.value_field)
        return (
            str(value).strip()
            if isinstance(value, str) and value.strip()
            else cls.title
        )

    @abstractmethod
    def run(self, ctx: ToolContext, args: Any) -> ToolOutcome: ...


def tech(name: str, label: str | None = None) -> Identity:
    return Identity(kind=IdentityKind.TECH.value, value=name, label=label)


def flag(country: str, label: str | None = None) -> Identity:
    return Identity(kind=IdentityKind.FLAG.value, value=country, label=label)


def favicon(url: str, label: str | None = None) -> Identity:
    return Identity(kind=IdentityKind.FAVICON.value, value=url, label=label)


def glyph(slug: str, label: str | None = None) -> Identity:
    return Identity(kind=IdentityKind.GLYPH.value, value=slug, label=label)


def nameserver(host: str, label: str | None = None) -> Identity:
    """The frontend resolves the provider from the hostname."""
    return Identity(kind=IdentityKind.NAMESERVER.value, value=host, label=label)


def lookup(value: str, tool: str) -> Lookup | None:
    """A value that another tool answers."""
    return Lookup(value=value.strip(), tool=tool) if value and value.strip() else None


def hero(
    headline: str,
    *,
    sub: str | None = None,
    identity: Identity | None = None,
    metric: Metric | None = None,
    meter: Meter | None = None,
    marks: list[Mark] | None = None,
    tone: str = Tone.NEUTRAL.value,
) -> Block:
    return Block(
        kind=BlockKind.HERO.value,
        headline=headline,
        sub=sub,
        identity=identity,
        metric=metric,
        meter=meter,
        marks=[m for m in (marks or []) if m is not None],
        tone=tone,
    )


def metric(
    value: Any, label: str | None = None, *, tone: str = Tone.NEUTRAL.value
) -> Metric | None:
    text = "" if value is None else str(value).strip()
    return Metric(value=text, label=label, tone=tone) if text else None


def meter(
    value: float,
    *,
    label: str | None = None,
    caption: str | None = None,
    tone: str = Tone.NEUTRAL.value,
) -> Meter:
    return Meter(
        value=max(0.0, min(1.0, value)), label=label, caption=caption, tone=tone
    )


def mark(
    label: str, *, tone: str = Tone.NEUTRAL.value, note: str | None = None
) -> Mark:
    return Mark(label=label, tone=tone, note=note)


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
    identity: Identity | None = None,
    lookup: Lookup | None = None,
) -> Fact | None:
    """A row, or None when the value is blank."""
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    return Fact(
        label=label,
        value=text,
        tone=tone,
        note=note,
        href=href,
        mono=mono,
        identity=identity,
        lookup=lookup,
    )


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
    identity: Identity | None = None,
    lookup: Lookup | None = None,
) -> Cell:
    return Cell(
        value="" if value is None else str(value),
        tone=tone,
        note=note,
        href=href,
        mono=mono,
        identity=identity,
        lookup=lookup,
    )


def tags(
    values: list[Tag], *, title: str | None = None, empty: str | None = None
) -> Block:
    return Block(kind=BlockKind.TAGS.value, title=title, tags=values, empty=empty)


def tag(
    value: str,
    *,
    tone: str = Tone.NEUTRAL.value,
    note: str | None = None,
    href: str | None = None,
    identity: Identity | None = None,
    lookup: Lookup | None = None,
) -> Tag:
    return Tag(
        value=value,
        tone=tone,
        note=note,
        href=href,
        identity=identity,
        lookup=lookup,
    )


def code(text: str, *, lang: str | None = None, title: str | None = None) -> Block:
    return Block(kind=BlockKind.CODE.value, title=title, text=text, lang=lang)


def image(src: str, *, title: str | None = None, sub: str | None = None) -> Block:
    return Block(kind=BlockKind.IMAGE.value, title=title, src=src, sub=sub)


def note(text: str, *, tone: str = Tone.INFO.value) -> Block:
    return Block(kind=BlockKind.NOTE.value, text=text, tone=tone)
