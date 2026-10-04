from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginUrl(BaseModel):
    audience: str
    host: str
    scheme: str | None = None
    port: int | None = None
    path: str | None = None
    credentials: int = 0


class NamedCount(BaseModel):
    name: str
    count: int | None = None


class InfostealerReport(BaseModel):
    domain: str
    total: int = 0
    employees: int = 0
    users: int = 0
    third_parties: int = 0
    total_urls: int = 0
    last_employee_at: datetime | None = None
    last_user_at: datetime | None = None
    logins: list[LoginUrl] = Field(default_factory=list)
    families: list[NamedCount] = Field(default_factory=list)
    passwords: dict[str, dict[str, int]] = Field(default_factory=dict)
    applications: list[NamedCount] = Field(default_factory=list)
    services: list[NamedCount] = Field(default_factory=list)
