"""AI services on web assets: the one writer of http_assets.ai_* and subdomains.ai_services."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import bindparam, text, update
from sqlalchemy.orm import Session

from shared.definitions.ai_services import (
    GENERIC_SERVICE,
    MAX_ENDPOINT_LENGTH,
    MAX_MODEL_LENGTH,
    MAX_MODELS,
    MAX_SERVICE_LENGTH,
    normalise_category,
)
from shared.models.http_asset import HttpAsset
from shared.utils.text import strip_control


@dataclass
class Detection:
    service: str
    category: str
    specificity: int
    endpoint: str
    models: list[str] = field(default_factory=list)


def detection(
    service: str,
    raw_category: str | None,
    specificity: int,
    endpoint: str,
    models: Iterable[str] = (),
) -> Detection:
    """A julius match, capped and scrubbed to what the columns hold."""
    key = strip_control(service).strip().lower()[:MAX_SERVICE_LENGTH]
    seen: list[str] = []
    for model in models:
        name = strip_control(str(model)).strip()[:MAX_MODEL_LENGTH]
        if name and name not in seen:
            seen.append(name)
        if len(seen) >= MAX_MODELS:
            break
    return Detection(
        service=key,
        category=normalise_category(raw_category, key),
        specificity=specificity,
        endpoint=(strip_control(endpoint) or "/")[:MAX_ENDPOINT_LENGTH],
        models=seen,
    )


def best(candidates: Iterable[Detection]) -> Detection | None:
    """The most specific match, the generic OpenAI shape only when nothing else matched."""
    ranked = sorted(
        candidates,
        key=lambda d: (d.service == GENERIC_SERVICE, -d.specificity, d.service),
    )
    if not ranked:
        return None
    top = ranked[0]
    if not top.models:
        for other in ranked[1:]:
            if other.models:
                top.models = list(other.models)
                break
    return top


_ASSET_UPDATE = (
    update(HttpAsset)
    .where(HttpAsset.id == bindparam("b_id"))
    .values(
        ai_checked=True,
        ai_service=bindparam("b_service"),
        ai_category=bindparam("b_category"),
        ai_endpoint=bindparam("b_endpoint"),
        ai_models=bindparam("b_models"),
    )
)


def record(session: Session, verdicts: dict[UUID, Detection | None]) -> int:
    """Mark every probed asset checked and store what answered on it."""
    if not verdicts:
        return 0
    rows = [
        {
            "b_id": asset_id,
            "b_service": found.service if found else None,
            "b_category": found.category if found else None,
            "b_endpoint": found.endpoint if found else None,
            "b_models": found.models if found and found.models else None,
        }
        for asset_id, found in sorted(verdicts.items(), key=lambda item: str(item[0]))
    ]
    session.connection().execute(_ASSET_UPDATE, rows)
    return len(rows)


_FOLD_SQL = text(
    """
    WITH per_host AS (
      SELECT a.host,
             coalesce(
               jsonb_agg(DISTINCT a.ai_service ORDER BY a.ai_service)
                 FILTER (WHERE a.ai_service IS NOT NULL),
               '[]'::jsonb
             ) AS services
      FROM http_assets a
      WHERE a.scan_id = :scan_id
        AND a.ai_checked
        AND (CAST(:hosts AS text[]) IS NULL OR a.host = ANY(CAST(:hosts AS text[])))
      GROUP BY a.host
    )
    UPDATE subdomains s
       SET ai_services = per_host.services::json
      FROM per_host
     WHERE s.scan_id = :scan_id AND s.name = per_host.host
    """
)


def fold_onto_hosts(
    session: Session, scan_id: UUID, hosts: Iterable[str] | None = None
) -> int:
    """The services every host's web assets answered with, on the host row."""
    names = None if hosts is None else sorted(set(hosts))
    return session.execute(_FOLD_SQL, {"scan_id": scan_id, "hosts": names}).rowcount


__all__ = ["Detection", "best", "detection", "fold_onto_hosts", "record"]
