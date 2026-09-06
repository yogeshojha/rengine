"""Shipped themes are indexed from disk on read; uploads live in the same table."""

from __future__ import annotations

from sqlalchemy import select

from reports.theme import ThemeError, builtin_source, builtin_themes, parse
from shared.definitions.report_theme import ThemeOrigin, ThemeTokens
from shared.definitions.reports import DEFAULT_THEME
from shared.models.report import ReportTheme
from shared.utils.datetime import utc_now


def sync_builtin(session) -> int:
    changed = 0
    for slug, tokens in builtin_themes().items():
        source = builtin_source(slug)
        row = (
            session.execute(select(ReportTheme).where(ReportTheme.slug == slug))
            .scalars()
            .first()
        )
        values = {
            "name": tokens.name,
            "description": tokens.description,
            "author": tokens.author,
            "version": tokens.version,
            "origin": ThemeOrigin.BUILTIN.value,
            "tokens": tokens.model_dump(),
            "source": source,
            "updated_at": utc_now(),
        }
        if row is None:
            session.add(ReportTheme(slug=slug, **values))
            changed += 1
        elif row.source != source:
            for key, value in values.items():
                setattr(row, key, value)
            session.add(row)
            changed += 1
    if changed:
        session.commit()
    return changed


def load(session, slug: str | None) -> ThemeTokens:
    key = (slug or "").strip() or DEFAULT_THEME
    row = (
        session.execute(select(ReportTheme).where(ReportTheme.slug == key))
        .scalars()
        .first()
    )
    if row is not None:
        try:
            return ThemeTokens.model_validate(row.tokens)
        except ValueError:
            pass
    shipped = builtin_themes()
    if key in shipped:
        return shipped[key]
    return shipped.get(DEFAULT_THEME) or ThemeTokens(key=DEFAULT_THEME, name="Default")


def validate(source: str, *, slug: str = "") -> ThemeTokens:
    return parse(source, slug=slug)


__all__ = ["ThemeError", "load", "sync_builtin", "validate"]
