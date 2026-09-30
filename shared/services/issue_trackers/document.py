"""A tracker-neutral issue body and its Markdown, Jira wiki and Jira ADF renderings."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal

from shared.definitions.issue_trackers import BodyFormat

BlockKind = Literal["heading", "paragraph", "facts", "code", "list", "link"]

_WIKI_SPECIAL = re.compile(r"([\\{}\[\]|*_+^~#!?-])")
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]<>#|@~])")
_NOFORMAT = re.compile(r"\{noformat\}", re.IGNORECASE)


@dataclass
class Block:
    kind: BlockKind
    text: str = ""
    items: list[tuple[str, str]] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    href: str = ""
    lang: str = ""


@dataclass
class Doc:
    blocks: list[Block] = field(default_factory=list)

    def heading(self, text: str) -> Doc:
        self.blocks.append(Block("heading", text=text))
        return self

    def paragraph(self, text: str | None) -> Doc:
        if text and text.strip():
            self.blocks.append(Block("paragraph", text=text.strip()))
        return self

    def facts(self, items: list[tuple[str, str | None]]) -> Doc:
        kept = [(k, str(v)) for k, v in items if v not in (None, "", [])]
        if kept:
            self.blocks.append(Block("facts", items=kept))
        return self

    def code(self, text: str | None, lang: str = "") -> Doc:
        if text and text.strip():
            self.blocks.append(Block("code", text=text.rstrip(), lang=lang))
        return self

    def bullets(self, lines: list[str]) -> Doc:
        kept = [line for line in lines if line]
        if kept:
            self.blocks.append(Block("list", lines=kept))
        return self

    def link(self, text: str, href: str) -> Doc:
        if href:
            self.blocks.append(Block("link", text=text, href=href))
        return self


def _fence(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _md(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", text)


def to_markdown(doc: Doc) -> str:
    out: list[str] = []
    for block in doc.blocks:
        if block.kind == "heading":
            out.append(f"### {_md(block.text)}")
        elif block.kind == "paragraph":
            out.append(_md(block.text))
        elif block.kind == "facts":
            out.append("\n".join(f"- **{_md(k)}:** {_md(v)}" for k, v in block.items))
        elif block.kind == "code":
            fence = _fence(block.text)
            out.append(f"{fence}{block.lang}\n{block.text}\n{fence}")
        elif block.kind == "list":
            out.append("\n".join(f"- {_md(line)}" for line in block.lines))
        elif block.kind == "link":
            out.append(f"[{_md(block.text)}]({block.href})")
    return "\n\n".join(out) + "\n"


def _wiki(text: str) -> str:
    return _WIKI_SPECIAL.sub(r"\\\1", text)


def to_wiki(doc: Doc) -> str:
    out: list[str] = []
    for block in doc.blocks:
        if block.kind == "heading":
            out.append(f"h3. {_wiki(block.text)}")
        elif block.kind == "paragraph":
            out.append(_wiki(block.text))
        elif block.kind == "facts":
            out.append("\n".join(f"* *{_wiki(k)}:* {_wiki(v)}" for k, v in block.items))
        elif block.kind == "code":
            body = _NOFORMAT.sub("{ noformat}", block.text)
            out.append(f"{{noformat}}\n{body}\n{{noformat}}")
        elif block.kind == "list":
            out.append("\n".join(f"* {_wiki(line)}" for line in block.lines))
        elif block.kind == "link":
            out.append(f"[{_wiki(block.text)}|{block.href}]")
    return "\n\n".join(out) + "\n"


def _text(value: str, *, strong: bool = False, href: str = "") -> dict:
    node: dict = {"type": "text", "text": value}
    marks = []
    if strong:
        marks.append({"type": "strong"})
    if href:
        marks.append({"type": "link", "attrs": {"href": href}})
    if marks:
        node["marks"] = marks
    return node


def _para(*content: dict) -> dict:
    return {"type": "paragraph", "content": list(content)}


def _bullets(items: list[list[dict]]) -> dict:
    return {
        "type": "bulletList",
        "content": [{"type": "listItem", "content": [_para(*item)]} for item in items],
    }


def to_adf(doc: Doc) -> dict:
    content: list[dict] = []
    for block in doc.blocks:
        if block.kind == "heading":
            content.append(
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [_text(block.text)],
                }
            )
        elif block.kind == "paragraph":
            content.append(_para(_text(block.text)))
        elif block.kind == "facts":
            content.append(
                _bullets(
                    [[_text(f"{k}: ", strong=True), _text(v)] for k, v in block.items]
                )
            )
        elif block.kind == "code":
            content.append({"type": "codeBlock", "content": [_text(block.text)]})
        elif block.kind == "list":
            content.append(_bullets([[_text(line)] for line in block.lines]))
        elif block.kind == "link":
            content.append(_para(_text(block.text, href=block.href)))
    return {"type": "doc", "version": 1, "content": content}


def rendered_size(doc: Doc, body_format: str) -> int:
    """Characters the tracker counts against its limit."""
    if body_format == BodyFormat.ADF.value:
        return len(json.dumps(to_adf(doc)))
    if body_format == BodyFormat.WIKI.value:
        return len(to_wiki(doc))
    return len(to_markdown(doc))
