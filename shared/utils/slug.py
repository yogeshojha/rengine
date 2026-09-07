import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

_ASCII = re.compile(r"[^a-z0-9\s-]")
_WORD = re.compile(r"[^\w\s-]", re.UNICODE)
_SEPARATORS = re.compile(r"[\s_]+")
_RUNS = re.compile(r"-+")

MAX_SLUG_ATTEMPTS = 50
FALLBACK_SLUG = "untitled"


def _reduce(pattern: re.Pattern[str], name: str) -> str:
    slug = pattern.sub("", name.lower().strip())
    slug = _SEPARATORS.sub("-", slug)
    return _RUNS.sub("-", slug).strip("-")


def generate_slug(name: str) -> str:
    """A name written in a non-Latin script still has to produce an addressable slug."""
    return _reduce(_ASCII, name) or _reduce(_WORD, name)


def _pending[T](
    session: AsyncSession, model: type[T], scope: dict[str, Any]
) -> set[str]:
    taken = set()
    for obj in session.new:
        if not isinstance(obj, model):
            continue
        if all(getattr(obj, key, None) == value for key, value in scope.items()):
            taken.add(getattr(obj, "slug", None))
    return taken


async def unique_slug[T](
    session: AsyncSession, model: type[T], name: str, **scope: Any
) -> str:
    """Slugs are constrained per scope, and a name maps to one many-to-one — so suffix until free."""
    base = generate_slug(name) or FALLBACK_SLUG
    conditions = [getattr(model, key) == value for key, value in scope.items()]
    uncommitted = _pending(session, model, scope)
    for attempt in range(1, MAX_SLUG_ATTEMPTS + 1):
        slug = base if attempt == 1 else f"{base}-{attempt}"
        if slug in uncommitted:
            continue
        rows = await session.execute(
            select(model.id).where(model.slug == slug, *conditions).limit(1)
        )
        if rows.scalar_one_or_none() is None:
            return slug
    return f"{base}-{uuid.uuid4().hex[:8]}"


def _slug_conflict(exc: IntegrityError) -> bool:
    inner = getattr(exc.orig, "__cause__", None) or exc.orig
    return "slug" in (getattr(inner, "constraint_name", None) or "")


async def add_with_unique_slug[T](
    session: AsyncSession, row: T, name: str, **scope: Any
) -> T:
    """The slug is constrained in the database, so a concurrent claim has to be retried, not pre-checked."""
    for _ in range(MAX_SLUG_ATTEMPTS):
        row.slug = await unique_slug(session, type(row), name, **scope)
        try:
            async with session.begin_nested():
                session.add(row)
                await session.flush()
        except IntegrityError as exc:
            if not _slug_conflict(exc):
                raise
            continue
        return row
    msg = f"Could not derive a free slug for {name!r}"
    raise RuntimeError(msg)
