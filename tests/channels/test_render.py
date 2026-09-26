"""Messages fit the channel, entities point at the right code units, target text stays literal."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from channels import render
from channels.commands import CommandError
from channels.dispatch import Dispatcher
from channels.models import ChannelChat
from channels.render import bold, chunk, code, data_lines, line, link, result_lines
from mcp.result import ToolResult

pytestmark = pytest.mark.channels


def _utf16(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def test_chunk_never_exceeds_the_limit():
    lines = [line(f"row {i} " + "x" * 90) for i in range(200)]
    for message in chunk(lines, 4000):
        assert len(message.text) <= 4000


def test_a_line_longer_than_the_limit_is_split():
    messages = chunk([line("a" * 9000)], 4000)
    assert [len(m.text) for m in messages] == [4000, 4000, 1000]


def test_a_message_fits_the_limit_in_code_units_not_characters():
    messages = chunk([line("🔥" * 60) for _ in range(40)], 400)
    assert messages
    for message in messages:
        assert _utf16(message.text) <= 400


def test_an_emoji_is_never_split_across_two_messages():
    messages = chunk([line("🔥" * 9)], 5)
    assert "".join(m.text for m in messages) == "🔥" * 9
    assert all(_utf16(m.text) <= 5 for m in messages)


def test_entities_use_utf16_offsets():
    messages = chunk(
        [
            line("🔥 ", bold("Résumé"), " ", code("id")),
            line(link("Open", "https://x.io")),
        ],
        4000,
    )
    message = messages[0]
    text = message.text
    for entity in message.entities:
        units = text.encode("utf-16-le")
        start, length = entity["offset"] * 2, entity["length"] * 2
        piece = units[start : start + length].decode("utf-16-le")
        assert piece in {"Résumé", "id", "Open"}
    assert message.entities[0]["offset"] == _utf16("🔥 ")
    assert message.entities[-1] == {
        "type": "text_link",
        "offset": _utf16("🔥 Résumé id\n"),
        "length": 4,
        "url": "https://x.io",
    }


def test_target_written_markup_is_sent_as_literal_text():
    hostile = "*bold* _it_ `code` <b>x</b> [link](https://evil)"
    messages = chunk([line(hostile)], 4000)
    assert messages[0].text == hostile
    assert messages[0].entities == []


def test_data_lines_render_dicts_lists_and_ids():
    data = {
        "total": 3,
        "scan_id": "3f2a1b7c-0000-4000-8000-000000000000",
        "tags": ["a", "b"],
        "rows": [{"host": "a.example.com", "status": 200}, {"host": "b.example.com"}],
        "empty": [],
    }
    lines = data_lines(data)
    text = "\n".join("".join(s.text for s in ln) for ln in lines)
    assert "total: 3" in text
    assert "scan id: 3f2a1b7c" in text
    assert "tags: a, b" in text
    assert "rows (2)" in text
    assert f"{render.BULLET}host: a.example.com · status: 200" in text
    assert "empty" not in text


def test_rows_are_capped_with_a_count():
    lines = data_lines([{"n": i} for i in range(30)])
    text = "\n".join("".join(s.text for s in ln) for ln in lines)
    assert "… 10 more" in text


def test_result_lines_carry_summary_caveats_and_the_link():
    result = ToolResult(
        summary="3 findings match",
        data={"total": 3},
        pivot="https://ui.example.com/scans/x?tab=vulnerabilities",
        caveats=["Observed yesterday."],
    )
    lines = result_lines(result)
    assert lines[0][0].style == render.BOLD
    flat = [s for ln in lines for s in ln]
    assert any(
        s.style == render.ITALIC and s.text == "Observed yesterday." for s in flat
    )
    assert flat[-1].style == render.LINK
    assert flat[-1].url == "https://ui.example.com/scans/x?tab=vulnerabilities"


def test_objects_render_as_their_text_and_hashes_shorten():
    row = {
        "id": uuid.UUID("3f2a1b7c-0000-4000-8000-000000000000"),
        "seen": datetime(2026, 9, 15, 16, 29, tzinfo=UTC),
        "fingerprint": "30c9631a0c461e8c233d206e3c0de1ff4f0a419b3d610d934a7ccaecae9b61e9",
        "name": "a",
    }
    text = "".join(s.text for s in render._pairs(row))
    assert (
        text
        == "id: 3f2a1b7c · seen: 2026-09-15 16:29 · fingerprint: 30c9631a · name: a"
    )


def test_caveats_are_respelled_for_the_chat():
    text = Dispatcher._chat_text(
        "Observed 2026-09-15 14:31:24.119329+00:00 by scan "
        "da2e7cdd-d11d-4e66-a1ba-3843469deb18. Start one with start_scan. "
        "scan_status follows the run. Started by agent token 'x' via MCP."
    )
    assert text == (
        "Observed 2026-09-15 14:31 by scan da2e7cdd. Start one with /scan. "
        "/progress follows the run. Started by agent token 'x' from chat."
    )


async def test_an_unknown_scan_prefix_is_named(estate):
    chat = ChannelChat(
        channel="telegram", external_id="1", project_id=estate.project_id
    )
    with pytest.raises(CommandError, match="No scan matches zz"):
        await Dispatcher._expand_ids(Dispatcher, estate.session, chat, {"scan": "zz"})


def test_a_url_telegram_refuses_is_sent_as_copyable_text():
    """Telegram rejects the whole message when one entity URL is not a public URL."""
    for url in (
        "http://localhost:5173/targets/x",
        "http://127.0.0.1:8000/",
        "http://rengine/x",
    ):
        span = link("Open in reNgine", url)
        assert span.style == render.CODE, url
        assert span.url is None
        assert span.text == url


def test_a_real_url_is_still_a_link():
    span = link(
        "Open in reNgine", "https://rengine.example.com/surface/vulnerabilities"
    )
    assert span.style == render.LINK
    assert span.url == "https://rengine.example.com/surface/vulnerabilities"
