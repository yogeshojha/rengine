"""The only reader and writer of wordlist files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from shared.definitions.wordlists import (
    BUILTIN_ROOT,
    BUILTIN_WORDLISTS,
    CUSTOM_ROOT,
    MAX_WORD_LENGTH,
    BuiltinWordlist,
    WordlistOrigin,
    slugify,
)
from shared.models.wordlist import Wordlist
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


class WordlistError(Exception):
    """An upload that cannot be stored."""


def builtin_root() -> Path:
    return Path(BUILTIN_ROOT)


def custom_root() -> Path:
    return Path(CUSTOM_ROOT)


def _root_for(origin: str) -> Path:
    return builtin_root() if origin == WordlistOrigin.BUILTIN.value else custom_root()


def resolve_path(row: Wordlist) -> Path:
    """The file for a row, inside its root."""
    root = _root_for(row.origin).resolve()
    target = (root / row.filename).resolve()
    if not target.is_relative_to(root):
        msg = f"{row.slug} resolves outside the wordlist root"
        raise WordlistError(msg)
    return target


def _word(line: str) -> str | None:
    word = line.strip().lower()
    if not word or word.startswith("#") or len(word) > MAX_WORD_LENGTH:
        return None
    return word


def clean_words(raw: str) -> list[str]:
    """One word per line, deduped, order kept."""
    seen: set[str] = set()
    words: list[str] = []
    for line in raw.splitlines():
        word = _word(line)
        if word is None or word in seen:
            continue
        seen.add(word)
        words.append(word)
    return words


def read_lines(path: Path, limit: int) -> list[str]:
    """The first `limit` words of a file."""
    words: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            word = _word(line)
            if word is not None:
                words.append(word)
            if len(words) >= limit:
                break
    return words


def _custom_target(relative: str) -> Path:
    root = custom_root().resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        msg = "The filename resolves outside the wordlist root."
        raise WordlistError(msg)
    return target


def prepare_custom(filename: str, raw: str) -> tuple[str, list[str]]:
    """Validate an upload: its file under the custom root and its words."""
    words = clean_words(raw)
    if not words:
        msg = (
            "No usable words. Every line is blank, a comment or over "
            f"{MAX_WORD_LENGTH} characters."
        )
        raise WordlistError(msg)
    stem = slugify(Path(filename).stem) or "wordlist"
    relative = f"{stem}.txt"
    _custom_target(relative)
    return relative, words


def write_custom(relative: str, words: list[str]) -> None:
    """Write a prepared upload under the custom root."""
    custom_root().mkdir(parents=True, exist_ok=True)
    _custom_target(relative).write_text("\n".join(words) + "\n", encoding="utf-8")


def delete_custom(row: Wordlist) -> None:
    """Unlink a custom list."""
    if row.origin != WordlistOrigin.CUSTOM.value:
        msg = "Default wordlists are read-only."
        raise WordlistError(msg)
    path = resolve_path(row)
    path.unlink(missing_ok=True)


def builtin_values(spec: BuiltinWordlist, path: Path, now: datetime) -> dict[str, Any]:
    """The row columns for a shipped list."""
    return {
        "name": spec.name,
        "description": spec.description,
        "origin": WordlistOrigin.BUILTIN.value,
        "kind": spec.kind,
        "filename": spec.filename,
        "words": len(clean_words(path.read_text(encoding="utf-8", errors="replace"))),
        "bytes": path.stat().st_size,
        "updated_at": now,
    }


def ensure_builtin(session: Session) -> int:
    """Index the shipped lists."""
    root = builtin_root()
    now = utc_now()
    indexed = 0
    changed = False
    for spec in BUILTIN_WORDLISTS:
        path = root / spec.filename
        if not path.is_file():
            continue
        indexed += 1
        row = session.scalar(select(Wordlist).where(Wordlist.slug == spec.slug))
        values = builtin_values(spec, path, now)
        if row is None:
            session.add(Wordlist(slug=spec.slug, **values))
            changed = True
        elif any(
            getattr(row, key) != value
            for key, value in values.items()
            if key != "updated_at"
        ):
            for key, value in values.items():
                setattr(row, key, value)
            session.add(row)
            changed = True
    if changed:
        session.commit()
    return indexed


def _builtin_by_filename(value: str) -> str | None:
    name = Path(value).name
    for spec in BUILTIN_WORDLISTS:
        if spec.filename == name:
            return spec.slug
    return None


def lookup(session: Session, reference: str) -> Wordlist | None:
    """Find a list by slug or by builtin filename."""
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
        msg = f"The file for {row.name} is missing."
        raise WordlistError(msg)
    return read_lines(path, limit), row.name


__all__ = [
    "WordlistError",
    "builtin_root",
    "builtin_values",
    "clean_words",
    "custom_root",
    "delete_custom",
    "ensure_builtin",
    "lookup",
    "prepare_custom",
    "read_lines",
    "read_words",
    "resolve_path",
    "write_custom",
]
