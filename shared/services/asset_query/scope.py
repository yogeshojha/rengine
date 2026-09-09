from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import false


@dataclass(frozen=True)
class QueryScope:
    """The scans a query reads: one on a scan page, one per target on a project view."""

    ids: tuple[UUID, ...]
    project_id: UUID | None = None

    @classmethod
    def of(cls, value: ScopeLike) -> QueryScope:
        if isinstance(value, QueryScope):
            return value
        if isinstance(value, UUID):
            return cls((value,))
        return cls(tuple(value))

    @property
    def single(self) -> UUID | None:
        return self.ids[0] if len(self.ids) == 1 else None

    def match(self, column):
        if not self.ids:
            return false()
        one = self.single
        return column == one if one is not None else column.in_(self.ids)

    def __bool__(self) -> bool:
        return bool(self.ids)


ScopeLike = UUID | QueryScope | Sequence[UUID]


def scope_of(value: ScopeLike) -> QueryScope:
    return QueryScope.of(value)


def scan_filter(column, value: ScopeLike):
    return QueryScope.of(value).match(column)
