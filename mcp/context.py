"""Everything a tool is given: a session, who is asking, and what they may do."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mcp.capabilities import Capability
from mcp.errors import CapabilityError, ScopeError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class TokenIdentity:
    id: uuid.UUID
    name: str
    project_id: uuid.UUID | None
    capabilities: frozenset[str]
    # the operator who issued the token; anything an agent writes is audited to them
    issued_by: uuid.UUID | None = None

    def allows(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass
class ToolContext:
    session: AsyncSession
    token: TokenIdentity
    ui_base_url: str
    client: str = "unknown"
    extras: dict = field(default_factory=dict)

    def require(self, capability: str | Capability) -> None:
        value = str(capability)
        if not self.token.allows(value):
            msg = f"This token may not {value}. Issue a token with the {value} capability."
            raise CapabilityError(msg)

    def scoped_projects(self) -> list[uuid.UUID] | None:
        """None means every project; the token was issued without a project."""
        return None if self.token.project_id is None else [self.token.project_id]

    def check_project(self, project_id: uuid.UUID) -> uuid.UUID:
        if self.token.project_id is not None and project_id != self.token.project_id:
            msg = "That project is outside this token's scope."
            raise ScopeError(msg)
        return project_id
