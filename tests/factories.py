"""Stages built through their own constructor, on a context a test only partly names."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from shared.enums.target import TargetType
from shared.services.scan_resolve import ResolvedScanConfig
from stages.base import Stage, StageContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def build_stage[S: Stage](
    stage: type[S], session: Session | Any = None, **context: Any
) -> S:
    """A stage on a real `StageContext`: ids a test leaves out are fresh, the target
    is `example.com` and the resolved config is the default one for that target."""
    fields: dict[str, Any] = {
        "scan_id": uuid.uuid4(),
        "target_id": uuid.uuid4(),
        "project_id": uuid.uuid4(),
        "target_value": "example.com",
        "target_type": TargetType.DOMAIN.value,
        **context,
    }
    fields.setdefault(
        "resolved",
        ResolvedScanConfig(
            target_value=fields["target_value"], target_type=fields["target_type"]
        ),
    )
    return stage(session, StageContext(**fields))
