from __future__ import annotations

import uuid
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import DBAPIError

from shared.services import endpoint_inventory, vuln_inventory

pytestmark = pytest.mark.pipeline

NUL = "\x00"
REFUSALS = [
    ValueError("A string literal cannot contain NUL (0x00) characters."),
    DBAPIError("INSERT", {}, Exception("invalid byte sequence for encoding")),
]


class _Refusing:
    """A sync session that refuses any row carrying a NUL."""

    def __init__(self, error: Exception):
        self.error = error
        self.stored: list[dict] = []

    def begin_nested(self):
        return nullcontext()

    def execute(self, _statement, rows: list[dict]):
        if any(NUL in str(value) for row in rows for value in row.values()):
            raise self.error
        self.stored.extend(rows)
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: rows))


@pytest.mark.parametrize("error", REFUSALS, ids=["psycopg", "asyncpg"])
def test_a_refused_response_is_dropped_and_counted(monkeypatch, error):
    monkeypatch.setattr(endpoint_inventory, "_response_upsert", lambda: None)
    session = _Refusing(error)
    kept, refused = uuid.uuid4(), uuid.uuid4()
    rows = [
        {"endpoint_id": kept, "response_body": "<html>ok</html>"},
        {"endpoint_id": refused, "response_body": f"bad{NUL}body"},
    ]

    assert endpoint_inventory._store_responses(session, rows) == 1
    assert [row["endpoint_id"] for row in session.stored] == [kept]


@pytest.mark.parametrize("error", REFUSALS, ids=["psycopg", "asyncpg"])
def test_a_refused_finding_is_dropped_and_the_rest_written(monkeypatch, error):
    monkeypatch.setattr(vuln_inventory, "_statement", lambda: None)
    session = _Refusing(error)
    chunk = [{"fingerprint": f"fp{n}", "response": "ok"} for n in range(4)]
    chunk[2]["response"] = f"bad{NUL}"

    assert vuln_inventory._insert(session, chunk) == 3
    assert [row["fingerprint"] for row in session.stored] == ["fp0", "fp1", "fp3"]
