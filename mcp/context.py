"""Everything a tool is given: a session, who is asking, and what they may do."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from mcp.capabilities import Capability
from mcp.errors import CapabilityError, ScopeError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Transport(StrEnum):
    HTTP = "http"
    STDIO = "stdio"


@dataclass(frozen=True)
class TokenIdentity:
    id: uuid.UUID
    name: str
    project_id: uuid.UUID | None
    capabilities: frozenset[str]
    issued_by: uuid.UUID | None = None
    # null means every target of the project
    targets: frozenset[uuid.UUID] | None = None

    def allows(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass
class ToolContext:
    session: AsyncSession
    token: TokenIdentity
    ui_base_url: str
    # set by the server: a Transport, ask or a channel kind
    client: str = "unknown"
    # what the caller says it is
    agent: str | None = None
    extras: dict = field(default_factory=dict)

    def require(self, capability: str | Capability) -> None:
        value = str(capability)
        if not self.token.allows(value):
            msg = f"This token lacks the {value} capability."
            raise CapabilityError(msg)

    def scoped_projects(self) -> list[uuid.UUID] | None:
        """None means every project."""
        return None if self.token.project_id is None else [self.token.project_id]

    def scoped_targets(self) -> frozenset[uuid.UUID] | None:
        """None means every target of the scoped projects."""
        return self.token.targets

    def check_project(self, project_id: uuid.UUID) -> uuid.UUID:
        if self.token.project_id is not None and project_id != self.token.project_id:
            msg = "The project is outside this token's scope."
            raise ScopeError(msg)
        return project_id

    def check_target(self, target_id: uuid.UUID | None) -> None:
        targets = self.token.targets
        if targets is not None and target_id not in targets:
            msg = "The target is outside this token's scope."
            raise ScopeError(msg)
