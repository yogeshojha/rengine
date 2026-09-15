"""Mine one scan's stored responses. The stage and the backfill both call this."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from shared.definitions.secrets import (
    BACKFILL_SCANS_PER_TICK,
    BODY_CAP_BYTES,
    DETECTORS_BY_KEY,
    WRITE_BATCH,
    MinerSource,
    SecretSource,
)
from shared.definitions.vulnerabilities import CoverageStatus
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanScope
from shared.logging import get_logger
from shared.models.http_asset import HttpAsset
from shared.services.locks import secret_mining as mining_lock
from shared.services.locks import sync_lock
from shared.services.secret_mining.detectors import Sweep, detector_count, find
from shared.services.secret_mining.inventory import (
    CoverageFacts,
    Observation,
    SecretInventory,
)
from shared.services.secret_mining.record import context, fingerprint
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_CHUNK = 200
_PROGRESS_EVERY = 500
CANCELLED = "The scan was cancelled."
BUSY = "Another miner holds this scan."


@dataclass
class MineOutcome:
    documents_total: int = 0
    documents_read: int = 0
    bytes_read: int = 0
    truncated: int = 0
    skipped: int = 0
    matches: int = 0
    secrets: int = 0
    sightings: int = 0
    dropped: dict[str, int] = field(default_factory=dict)
    aborted: bool = False
    busy: bool = False


@dataclass(frozen=True)
class _Document:
    asset_id: uuid.UUID
    host: str
    url: str
    source: str
    text: str


def observations_for(sweep: Sweep, doc: _Document) -> list[Observation]:
    """Rows for every kept match in one document."""
    out: list[Observation] = []
    for match in sweep.matches:
        spec = DETECTORS_BY_KEY[match.kind]
        out.append(
            Observation(
                fingerprint=fingerprint(match.kind, match.value),
                kind=spec.key,
                group=spec.group,
                vendor=spec.vendor,
                state=match.state,
                is_secret=not spec.public,
                value=match.value,
                subject=match.subject,
                meta=match.meta,
                host=doc.host,
                url=doc.url,
                http_asset_id=doc.asset_id,
                source=doc.source,
                offset=match.start,
                context=context(doc.text, match.start, match.end),
            )
        )
    return out


def _documents(row) -> list[_Document]:
    out: list[_Document] = []
    if row.response_body:
        out.append(
            _Document(
                row.id, row.host, row.url, SecretSource.BODY.value, row.response_body
            )
        )
    if row.raw_response_header:
        out.append(
            _Document(
                row.id,
                row.host,
                row.url,
                SecretSource.HEADER.value,
                row.raw_response_header,
            )
        )
    return out


def _has_text():
    return or_(
        HttpAsset.response_body.isnot(None), HttpAsset.raw_response_header.isnot(None)
    )


def mine_scan(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    aborted: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
    announce: Callable[[], None] | None = None,
) -> MineOutcome:
    """Read every stored response of the scan once and write what the detectors keep."""
    with sync_lock(session, mining_lock(scan_id)) as held:
        if not held:
            logger.warning(
                "secret mining skipped, scan is locked", scan_id=str(scan_id)
            )
            return MineOutcome(busy=True)
        return _mine_locked(
            session,
            scan_id=scan_id,
            target_id=target_id,
            project_id=project_id,
            aborted=aborted,
            on_progress=on_progress,
            announce=announce,
        )


def _mine_locked(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    aborted: Callable[[], bool] | None,
    on_progress: Callable[[str], None] | None,
    announce: Callable[[], None] | None,
) -> MineOutcome:
    started = utc_now()
    outcome = MineOutcome()
    inventory = SecretInventory(
        session, scan_id=scan_id, target_id=target_id, project_id=project_id
    )
    facts = CoverageFacts(
        source=MinerSource.STORED_RESPONSES.value,
        status=CoverageStatus.COMPLETED.value,
        detectors=detector_count(),
        started_at=started,
    )
    outcome.documents_total = int(
        session.scalar(
            select(func.count()).where(HttpAsset.scan_id == scan_id, _has_text())
        )
        or 0
    )
    buffer: list[Observation] = []

    def flush() -> None:
        if not buffer:
            return
        inventory.write(buffer)
        buffer.clear()
        if announce is not None:
            announce()

    try:
        ids = list(
            session.scalars(
                select(HttpAsset.id)
                .where(HttpAsset.scan_id == scan_id, _has_text())
                .order_by(HttpAsset.host, HttpAsset.url)
            ).all()
        )
        seen = 0
        for start in range(0, len(ids), _CHUNK):
            if aborted is not None and aborted():
                outcome.aborted = True
                break
            chunk = ids[start : start + _CHUNK]
            rows = session.execute(
                select(
                    HttpAsset.id,
                    HttpAsset.host,
                    HttpAsset.url,
                    HttpAsset.response_body,
                    HttpAsset.raw_response_header,
                ).where(HttpAsset.id.in_(chunk))
            ).all()
            for row in rows:
                docs = _documents(row)
                if not docs:
                    outcome.skipped += 1
                    continue
                outcome.documents_read += 1
                for doc in docs:
                    outcome.bytes_read += len(doc.text)
                    if (
                        doc.source == SecretSource.BODY.value
                        and len(doc.text) >= BODY_CAP_BYTES
                    ):
                        outcome.truncated += 1
                    sweep = find(doc.text, now=started)
                    for reason, n in sweep.dropped.items():
                        outcome.dropped[reason] = outcome.dropped.get(reason, 0) + n
                    outcome.matches += len(sweep.matches)
                    buffer.extend(observations_for(sweep, doc))
                seen += 1
                if len(buffer) >= WRITE_BATCH:
                    flush()
                if on_progress is not None and seen % _PROGRESS_EVERY == 0:
                    on_progress(
                        f"{seen:,} of {outcome.documents_total:,} responses read, "
                        f"{inventory.secrets:,} secrets"
                    )
        flush()
    except Exception as exc:
        session.rollback()
        facts.status = CoverageStatus.FAILED.value
        facts.error = str(exc)[:2000]
        _finish(inventory, facts, outcome)
        raise
    if outcome.aborted:
        facts.status = CoverageStatus.PARTIAL.value
        facts.error = CANCELLED
    _finish(inventory, facts, outcome)
    return outcome


def _finish(
    inventory: SecretInventory, facts: CoverageFacts, outcome: MineOutcome
) -> None:
    outcome.secrets = inventory.secrets
    outcome.sightings = inventory.sightings
    facts.documents_total = outcome.documents_total
    facts.documents_read = outcome.documents_read
    facts.bytes_read = outcome.bytes_read
    facts.truncated = outcome.truncated
    facts.skipped = outcome.skipped
    facts.matches = outcome.matches
    facts.secrets = outcome.secrets
    facts.dropped = dict(outcome.dropped)
    inventory.record_coverage(facts)


_PENDING = text(
    """
    SELECT s.id
      FROM scans s
     WHERE s.status = ANY(:statuses)
       AND s.scope = :scope
       AND (s.execution_config -> 'stages' -> 'secret_mining') IS NULL
       AND NOT EXISTS (SELECT 1 FROM secret_coverage c WHERE c.scan_id = s.id)
       AND EXISTS (
             SELECT 1 FROM http_assets a
              WHERE a.scan_id = s.id
                AND (a.response_body IS NOT NULL OR a.raw_response_header IS NOT NULL)
           )
     ORDER BY s.created_at DESC
     LIMIT :limit
    """
)


def pending_scans(
    session: Session, *, limit: int = BACKFILL_SCANS_PER_TICK
) -> list[uuid.UUID]:
    """Settled census runs from before the stage existed, newest first."""
    rows = session.execute(
        _PENDING,
        {
            "statuses": list(SCAN_TERMINAL_STATUSES),
            "scope": ScanScope.FULL.value,
            "limit": limit,
        },
    ).all()
    return [row[0] for row in rows]
