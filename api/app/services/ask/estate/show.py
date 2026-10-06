"""The tools only estate answers have: show a block, look up a value."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ask import tools
from app.services.ask.estate import blocks
from app.services.ask.estate.dimensions import DIMENSIONS, ROW_DIMENSIONS
from app.services.ask.estate.lookup import lookup
from app.services.ask.estate.scope import Resolved
from mcp import server, telemetry
from shared.definitions.ask import (
    BLOCK_ID,
    BLOCK_SAMPLE,
    MAX_BLOCKS_PER_ANSWER,
    MAX_BLOCKS_PER_THREAD,
    TOOL_TEXT_CHARS,
    BlockKind,
    TargetKey,
    TraceStatus,
)
from shared.models.ask import AnswerBlock, BlockData, TraceStep
from shared.services.ai.agent import AgentTool

SHOW_ROWS = "show_rows"
SHOW_GROUPS = "show_groups"
SHOW_CVE = "show_cve"
LOOKUP = "lookup_values"

LABELS: dict[str, str] = {
    SHOW_ROWS: "Show rows",
    SHOW_GROUPS: "Show groups",
    SHOW_CVE: "Show CVE",
    LOOKUP: "Look up values",
}
KINDS: dict[str, str] = {
    SHOW_ROWS: BlockKind.ROWS.value,
    SHOW_GROUPS: BlockKind.GROUPS.value,
    SHOW_CVE: BlockKind.CVE.value,
}
TOO_MANY = f"At most {MAX_BLOCKS_PER_ANSWER} blocks in one answer."
THREAD_FULL = f"This thread holds {MAX_BLOCKS_PER_THREAD} blocks. Ask in a new thread."
SHOWN = "{id} already shows this query. Add a clause to narrow it, or answer from {id}."

_ROW_DIMS = sorted(ROW_DIMENSIONS, key=list(DIMENSIONS).index)

AGENT_TOOLS: tuple[AgentTool, ...] = (
    AgentTool(
        SHOW_ROWS,
        "Put the rows of one dimension that match a query on the engineer's screen as "
        "the next block. Returns the block id, the exact count and the first rows. Use "
        "it for every set of rows the answer is about.",
        {
            "type": "object",
            "properties": {
                "dimension": {"type": "string", "enum": _ROW_DIMS},
                "query": {
                    "type": "string",
                    "description": "A query in the query language. Omit for every row.",
                },
                "title": {
                    "type": "string",
                    "description": (
                        "A noun phrase that reads after the count, under 7 words, "
                        "such as known exploited findings or WordPress web assets."
                    ),
                },
                "narrows": {
                    "type": "string",
                    "description": "The block this one narrows, such as B1.",
                },
            },
            "required": ["dimension"],
        },
    ),
    AgentTool(
        SHOW_GROUPS,
        "Put grouped counts of one dimension on the engineer's screen as the next "
        "block: by technology, status, network, severity, check and the other group "
        "keys. Each group carries the query that isolates it.",
        {
            "type": "object",
            "properties": {
                "dimension": {"type": "string", "enum": list(DIMENSIONS)},
                "group_by": {"type": "string", "description": "A group key."},
                "query": {
                    "type": "string",
                    "description": "Only rows matching this query are grouped.",
                },
                "title": {"type": "string"},
                "narrows": {"type": "string"},
            },
            "required": ["dimension", "group_by"],
        },
    ),
    AgentTool(
        SHOW_CVE,
        "Put one CVE's record on the engineer's screen as the next block: severity, "
        "CVSS, EPSS, known exploited, the assets in scope that carry it on the "
        "evidence ladder, and how many checks in the library look for it.",
        {
            "type": "object",
            "properties": {"cve": {"type": "string", "description": "CVE-2023-22527"}},
            "required": ["cve"],
        },
    ),
    AgentTool(
        LOOKUP,
        "How the estate spells a value. key is a group key of the dimension, such as "
        "tech, org, asn, cdn, server or template, or one of target, tag and "
        "organization. Returns the matching values with counts and the query that "
        "selects each. Shows nothing on screen.",
        {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "text": {"type": "string", "description": "Part of the value."},
                "dimension": {
                    "type": "string",
                    "enum": list(DIMENSIONS),
                    "description": "Needed for a group key. Defaults to web_assets.",
                },
            },
            "required": ["key", "text"],
        },
    ),
)

NAMES = frozenset(t.name for t in AGENT_TOOLS)
# the show tools replace these
REPLACED = frozenset({"query_assets", "group_assets"})
MAX_DETAIL = 200


@dataclass
class Board:
    """The blocks of one thread, and the ones this answer added."""

    project_id: uuid.UUID
    resolved: Resolved
    held: list[AnswerBlock]
    added: list[AnswerBlock] = field(default_factory=list)
    fresh: list[tuple[AnswerBlock, BlockData]] = field(default_factory=list)
    datas: dict[str, BlockData] = field(default_factory=dict)

    @property
    def every(self) -> list[AnswerBlock]:
        return [*self.held, *self.added]

    def next_id(self) -> str:
        return f"B{len(self.every) + 1}"


def _text(payload: dict) -> str:
    text = json.dumps(tools.scrub(payload), indent=1, default=str, ensure_ascii=False)
    return (
        text
        if len(text) <= TOOL_TEXT_CHARS
        else f"{text[:TOOL_TEXT_CHARS]}\nTruncated."
    )


def _for_model(data: BlockData) -> dict:
    out: dict = {"block": data.id, "summary": blocks.headline(data)}
    if data.covered is not None:
        out["targets_scanned_for_dimension"] = data.covered
    if data.rows:
        out["first_rows"] = [
            {k: v for k, v in row.items() if not k.startswith("_")}
            for row in data.rows[:BLOCK_SAMPLE]
        ]
    if data.groups:
        out["groups"] = [g.model_dump() for g in data.groups]
    whole = f"{data.total}{'+' if data.capped else ''}"
    if data.causes:
        out["shown_by"] = {
            "key": data.causes.key,
            "groups": data.causes.total_groups,
            "largest": [
                {
                    "value": c.value,
                    "count": f"{c.count} of {whole}",
                    ("network" if data.causes.address else "name"): c.who,
                    "top": [
                        f"{d.label} ({d.hint}) {d.count}"
                        if d.hint
                        else f"{d.label} {d.count}"
                        for d in c.details
                    ],
                }
                for c in data.causes.groups
            ],
        }
    if data.facts:
        out["counted_facts"] = [f"{f.count} of {whole} {f.title}" for f in data.facts]
    if data.record:
        out["record"] = data.record
    return out


def _narrows(value: object, board: Board) -> str | None:
    text = str(value or "").strip().upper()
    if BLOCK_ID.match(text) and any(b.id == text for b in board.every):
        return text
    return None


def _block(name: str, args: dict, board: Board) -> AnswerBlock:
    return AnswerBlock(
        id=board.next_id(),
        kind=KINDS[name],
        dimension=args.get("dimension") if name != SHOW_CVE else None,
        query=blocks.clean_query(args.get("query")),
        group_by=str(args.get("group_by") or "") or None,
        cve=str(args.get("cve") or "").strip().upper() or None,
        title=blocks.clean_title(args.get("title"), args.get("dimension")),
        about=_narrows(args.get("narrows"), board),
    )


def _same(block: AnswerBlock, board: Board) -> str | None:
    key = (block.kind, block.dimension, block.query, block.group_by, block.cve)
    return next(
        (
            b.id
            for b in board.added
            if (b.kind, b.dimension, b.query, b.group_by, b.cve) == key
        ),
        None,
    )


async def _show(
    session: AsyncSession, name: str, args: dict, board: Board
) -> tuple[str, int | None]:
    if len(board.added) >= MAX_BLOCKS_PER_ANSWER:
        raise blocks.BlockError(TOO_MANY)
    if len(board.every) >= MAX_BLOCKS_PER_THREAD:
        raise blocks.BlockError(THREAD_FULL)
    block = _block(name, args, board)
    if same := _same(block, board):
        raise blocks.BlockError(SHOWN.format(id=same))
    if name == SHOW_ROWS:
        data = await blocks.rows(
            session, board.project_id, board.resolved, block, pick=True
        )
    elif name == SHOW_GROUPS:
        data = await blocks.groups(session, board.project_id, board.resolved, block)
    else:
        data = await blocks.cve(session, board.project_id, board.resolved, block)
    block.total = data.total
    block.capped = data.capped
    board.added.append(block)
    board.fresh.append((block, data))
    board.datas[block.id] = data
    return _text(_for_model(data)), data.total


async def _lookup(session: AsyncSession, args: dict, board: Board) -> tuple[str, int]:
    key = str(args.get("key") or "").strip()
    dimension = args.get("dimension")
    if key not in {k.value for k in TargetKey} and not dimension:
        dimension = next(iter(DIMENSIONS))
    found = await lookup(
        session,
        board.project_id,
        board.resolved,
        key=key,
        text=str(args.get("text") or ""),
        dimension=dimension,
    )
    return _text(found), len(found.get("matches") or [])


def _plural(dimension: object) -> str:
    dim = DIMENSIONS.get(str(dimension or ""))
    return dim.noun_plural if dim else "rows"


def running(name: str, args: dict) -> str:
    """What a call is doing, while it runs."""
    if name in (SHOW_ROWS, SHOW_GROUPS):
        return f"Searching {_plural(args.get('dimension'))}"
    if name == SHOW_CVE:
        return f"Reading {str(args.get('cve') or 'the CVE').upper()}"
    if name == LOOKUP:
        return f"Looking up {str(args.get('text') or '')[:40]}".strip()
    return LABELS.get(name, name)


def _done(name: str, args: dict, board: Board) -> str:
    if name == LOOKUP:
        return f"Looked up {str(args.get('text') or '')[:40]}".strip()
    if not board.added:
        return LABELS[name]
    block = board.added[-1]
    if name == SHOW_CVE:
        return f"{block.cve} record"
    title = block.title or _plural(block.dimension).capitalize()
    return f"{block.id} · {title}"


async def call(
    session: AsyncSession, name: str, args: dict, board: Board
) -> tuple[str, TraceStep]:
    started = time.monotonic()

    def step(
        status: str,
        rows: int | None = None,
        detail: str | None = None,
        label: str | None = None,
    ):
        return TraceStep(
            tool=name,
            label=label or running(name, args),
            status=status,
            rows=rows,
            ms=int((time.monotonic() - started) * 1000),
            detail=detail,
            args=telemetry.phrase_args(args),
        )

    try:
        if name == LOOKUP:
            text, rows = await _lookup(session, args, board)
        else:
            text, rows = await _show(session, name, args, board)
    except blocks.BlockError as exc:
        return str(exc), step(TraceStatus.FAILED.value, detail=str(exc)[:MAX_DETAIL])
    except Exception as exc:
        await session.rollback()
        message = server.failed(LABELS[name], exc)
        return message, step(TraceStatus.FAILED.value, detail=message[:MAX_DETAIL])
    return text, step(TraceStatus.DONE.value, rows=rows, label=_done(name, args, board))
