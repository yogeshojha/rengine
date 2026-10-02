from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from reports.theme import builtin_source, builtin_themes
from shared.definitions.report_theme import ThemeOrigin, ThemeTokens
from shared.definitions.reports import DEFAULT_THEME
from shared.models.report import ReportTheme
from shared.utils.datetime import utc_now


def builtin_values(tokens: ThemeTokens, source: str) -> dict:
    return {
        "name": tokens.name,
        "description": tokens.description,
        "author": tokens.author,
        "version": tokens.version,
        "origin": ThemeOrigin.BUILTIN.value,
        "tokens": tokens.model_dump(),
        "source": source,
        "updated_at": utc_now(),
    }


def sync_builtin(session) -> int:
    changed = 0
    for slug, tokens in builtin_themes().items():
        source = builtin_source(slug)
        row = (
            session.execute(select(ReportTheme).where(ReportTheme.slug == slug))
            .scalars()
            .first()
        )
        values = builtin_values(tokens, source)
        if row is None:
            session.add(ReportTheme(slug=slug, **values))
            changed += 1
        elif row.source != source:
            for key, value in values.items():
                setattr(row, key, value)
            session.add(row)
            changed += 1
    if changed:
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return 0
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
