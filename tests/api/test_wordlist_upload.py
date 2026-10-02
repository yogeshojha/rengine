from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.api.v1.wordlists import upload_wordlists
from shared.definitions.wordlists import BuiltinWordlist, WordlistKind, WordlistOrigin
from shared.models.wordlist import Wordlist, WordlistFile, WordlistUploadRequest
from shared.services import wordlists

pytestmark = pytest.mark.api


@pytest.fixture
def root(tmp_path, monkeypatch, session):
    monkeypatch.setattr(wordlists, "CUSTOM_ROOT", str(tmp_path))
    monkeypatch.setattr(session, "commit", session.flush)
    return tmp_path


async def test_a_rejected_name_leaves_the_stored_file(session, root):
    stem = f"kept-{uuid.uuid4().hex[:8]}"
    taken = f"taken-{uuid.uuid4().hex[:8]}"
    (root / f"{stem}.txt").write_text("one\n", encoding="utf-8")
    session.add(
        Wordlist(
            slug=stem,
            name=stem,
            origin=WordlistOrigin.CUSTOM.value,
            filename=f"{stem}.txt",
            words=1,
            bytes=4,
        )
    )
    session.add(
        Wordlist(
            slug=taken,
            name=taken,
            origin=WordlistOrigin.CUSTOM.value,
            filename=f"{taken}.txt",
        )
    )
    await session.flush()

    result = await upload_wordlists(
        SimpleNamespace(id=uuid.uuid4()),
        session,
        WordlistUploadRequest(
            files=[WordlistFile(filename=f"{stem}.txt", content="two\n", name=taken)]
        ),
    )

    assert not result.stored
    assert [r.filename for r in result.rejected] == [f"{stem}.txt"]
    assert (root / f"{stem}.txt").read_text(encoding="utf-8") == "one\n"


async def test_an_accepted_upload_writes_its_words(session, root):
    stem = f"fresh-{uuid.uuid4().hex[:8]}"

    result = await upload_wordlists(
        SimpleNamespace(id=uuid.uuid4()),
        session,
        WordlistUploadRequest(
            files=[WordlistFile(filename=f"{stem}.txt", content="Admin\n#c\nadmin\n")]
        ),
    )

    assert [r.words for r in result.stored] == [1]
    assert (root / f"{stem}.txt").read_text(encoding="utf-8") == "admin\n"


async def test_an_unchanged_builtin_list_is_not_rewritten(
    session, tmp_path, monkeypatch
):
    slug = f"builtin-{uuid.uuid4().hex[:8]}"
    (tmp_path / f"{slug}.txt").write_text("admin\nlogin\n", encoding="utf-8")
    spec = BuiltinWordlist(
        slug=slug,
        filename=f"{slug}.txt",
        name=slug,
        kind=WordlistKind.CONTENT.value,
        description="",
    )
    monkeypatch.setattr(wordlists, "BUILTIN_ROOT", str(tmp_path))
    monkeypatch.setattr(wordlists, "BUILTIN_WORDLISTS", (spec,))
    commits: list[int] = []
    sync = session.sync_session
    monkeypatch.setattr(sync, "commit", lambda: commits.append(1) or sync.flush())

    await session.run_sync(wordlists.ensure_builtin)
    row = await session.scalar(select(Wordlist).where(Wordlist.slug == slug))
    stamp = row.updated_at
    await session.run_sync(wordlists.ensure_builtin)

    assert len(commits) == 1
    assert row.updated_at == stamp
