from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

ROW_LIMIT = 10000


class CrtShOrganization(BaseModel):
    name: str
    certs: int = 0
    domains: dict[str, date | None] = Field(default_factory=dict)


class CrtShResult(BaseModel):
    certs: int = 0
    organizations: list[CrtShOrganization] = Field(default_factory=list)
    stored_at: datetime | None = None

    @property
    def capped(self) -> bool:
        return self.certs >= ROW_LIMIT
