"""The only reader and writer of wordlist files. Every path resolves inside a known root."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select

from shared.definitions.wordlists import (
    BUILTIN_ROOT,
    BUILTIN_WORDLISTS,
    CUSTOM_ROOT,
    MAX_WORD_LENGTH,
    WordlistOrigin,
    slugify,
)
from shared.logging import get_logger
from shared.models.wordlist import Wordlist
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)


class WordlistError(Exception):
    """An upload that cannot be stored, with the reason a person needs."""


def builtin_root() -> Path:
    return Path(BUILTIN_ROOT)


def custom_root() -> Path:
    return Path(CUSTOM_ROOT)


def _root_for(origin: str) -> Path:
    return builtin_root() if origin == WordlistOrigin.BUILTIN.value else custom_root()


def resolve_path(row: Wordlist) -> Path:
    """The file for a row, or a refusal — a stored filename never escapes its root."""
    root = _root_for(row.origin).resolve()
    target = (root / row.filename).resolve()
    if not target.is_relative_to(root):
        msg = f"{row.slug} resolves outside the wordlist root"
        raise WordlistError(msg)
    return target


def clean_words(raw: str) -> list[str]:
    """One word per line, deduped, order kept — the order is the budget."""
    seen: set[str] = set()
    words: list[str] = []
    for line in raw.splitlines():
        word = line.strip().lower()
        if not word or word.startswith("#") or len(word) > MAX_WORD_LENGTH:
            continue
        if word in seen:
            continue
        seen.add(word)
        words.append(word)
    return words


def store_custom(filename: str, raw: str) -> tuple[str, list[str]]:
    """Validate an upload and write it under the custom root. Returns (filename, words)."""
    words = clean_words(raw)
    if not words:
        msg = "No usable words: every line was blank, a comment or over 63 characters."
        raise WordlistError(msg)
    stem = slugify(Path(filename).stem) or "wordlist"
    relative = f"{stem}.txt"
    root = custom_root()
    root.mkdir(parents=True, exist_ok=True)
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        msg = "Refusing to write outside the wordlist root."
        raise WordlistError(msg)
    target.write_text("\n".join(words) + "\n", encoding="utf-8")
    return relative, words


def delete_custom(row: Wordlist) -> None:
    """Only ever unlinks inside the custom root; a builtin list is never removed."""
    if row.origin != WordlistOrigin.CUSTOM.value:
        msg = "A shipped wordlist cannot be deleted."
        raise WordlistError(msg)
    path = resolve_path(row)
    path.unlink(missing_ok=True)


def ensure_builtin(session: Session) -> int:
    """Index the shipped lists so they sit beside uploads in the same picker."""
    root = builtin_root()
    now = utc_now()
    indexed = 0
    for spec in BUILTIN_WORDLISTS:
        path = root / spec.filename
        if not path.is_file():
            continue
        words = len(clean_words(path.read_text(encoding="utf-8", errors="replace")))
        row = session.scalar(select(Wordlist).where(Wordlist.slug == spec.slug))
        values = {
            "name": spec.name,
            "description": spec.description,
            "origin": WordlistOrigin.BUILTIN.value,
            "kind": spec.kind,
            "filename": spec.filename,
            "words": words,
            "bytes": path.stat().st_size,
            "updated_at": now,
        }
        if row is None:
            session.add(Wordlist(slug=spec.slug, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)
            session.add(row)
        indexed += 1
    session.commit()
    return indexed


def _builtin_by_filename(value: str) -> str | None:
    name = Path(value).name
    for spec in BUILTIN_WORDLISTS:
        if spec.filename == name:
            return spec.slug
    return None


def lookup(session: Session, reference: str) -> Wordlist | None:
    """Find a list by slug, tolerating the absolute paths older engines stored."""
    value = (reference or "").strip()
    if not value:
        return None
    row = session.scalar(select(Wordlist).where(Wordlist.slug == value))
    if row is not None:
        return row
    slug = _builtin_by_filename(value)
    if slug is None:
        return None
    ensure_builtin(session)
    return session.scalar(select(Wordlist).where(Wordlist.slug == slug))


def read_words(session: Session, reference: str, limit: int) -> tuple[list[str], str]:
    """The first `limit` words of a list, with the name to report it by."""
    row = lookup(session, reference)
    if row is None:
        msg = f"No wordlist named {reference!r} is in the library."
        raise WordlistError(msg)
    path = resolve_path(row)
    if not path.is_file():
        msg = f"{row.name} is in the library but its file is missing."
        raise WordlistError(msg)
    words: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            word = line.strip().lower()
            if word and not word.startswith("#") and len(word) <= MAX_WORD_LENGTH:
                words.append(word)
            if len(words) >= limit:
                break
    return words, row.name


__all__ = [
    "WordlistError",
    "builtin_root",
    "clean_words",
    "custom_root",
    "delete_custom",
    "ensure_builtin",
    "lookup",
    "read_words",
    "resolve_path",
    "store_custom",
]
