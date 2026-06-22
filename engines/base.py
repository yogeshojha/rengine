from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from shared.services.scan_resolve import ResolvedScanConfig


@dataclass
class EngineContext:
    scan_id: uuid.UUID
    target_id: uuid.UUID
    project_id: uuid.UUID
    target_value: str
    target_type: str
    resolved: ResolvedScanConfig


@dataclass
class EngineResult:
    counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class Engine(ABC):
    name: ClassVar[str]

    def __init__(self, session: Session, context: EngineContext) -> None:
        self.session = session
        self.ctx = context

    @abstractmethod
    def should_run(self) -> bool: ...

    @abstractmethod
    def run(self) -> EngineResult: ...
