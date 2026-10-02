"""Mine one scan's stored responses."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shared.definitions.secrets import (
    ALL_SOURCES,
    BACKFILL_SCANS_PER_TICK,
    DETECTORS_BY_KEY,
    STAGE_SOURCES,
    WRITE_BATCH,
)
from shared.definitions.vulnerabilities import CoverageStatus
from shared.enums.scan import SCAN_TERMINAL_STATUSES, ScanScope
from shared.logging import get_logger
from shared.models.secret import SecretCoverage
from shared.services.locks import secret_mining as mining_lock
from shared.services.locks import sync_lock
from shared.services.secret_mining.corpora import Corpus, Document, corpora_for
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
BUSY = "Secrets not mined. Another secret mining run is in progress on the same scan."


@dataclass
class MineOutcome:
    documents_read: int = 0
    truncated: int = 0
    secrets: int = 0
    aborted: bool = False
    busy: bool = False

    def absorb(self, facts: CoverageFacts) -> None:
        self.documents_read += facts.documents_read
        self.truncated += facts.truncated


def observations_for(sweep: Sweep, doc: Document) -> list[Observation]:
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


def mine_scan(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    sources: Sequence[str] = ALL_SOURCES,
    incremental: bool = False,
    aborted: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
    announce: Callable[[], None] | None = None,
) -> MineOutcome:
    """Read every stored response of the named corpora once and write what the detectors keep."""
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
            corpora=corpora_for(sources),
            incremental=incremental,
            aborted=aborted,
            on_progress=on_progress,
            announce=announce,
        )


class _Miner:
    def __init__(
        self,
        session: Session,
        inventory: SecretInventory,
        *,
        scan_id: uuid.UUID,
        aborted: Callable[[], bool] | None,
        on_progress: Callable[[str], None] | None,
        announce: Callable[[], None] | None,
    ) -> None:
        self.session = session
        self.inventory = inventory
        self.scan_id = scan_id
        self.aborted = aborted
        self.on_progress = on_progress
        self.announce = announce
        self.buffer: list[Observation] = []
        self.started = utc_now()

    def flush(self) -> None:
        if not self.buffer:
            return
        self.inventory.write(self.buffer)
        self.buffer.clear()
        if self.announce is not None:
            self.announce()

    def read(self, corpus: Corpus, facts: CoverageFacts) -> bool:
        """Read one corpus into the buffer. Returns False when the scan was aborted."""
        facts.documents_total = int(
            self.session.scalar(corpus.count(self.scan_id)) or 0
        )
        ids = list(self.session.scalars(corpus.ids(self.scan_id)).all())
        seen = 0
        for start in range(0, len(ids), _CHUNK):
            if self.aborted is not None and self.aborted():
                return False
            chunk = ids[start : start + _CHUNK]
            for row in self.session.execute(corpus.rows(chunk)).all():
                docs = corpus.documents(row)
                if not docs:
                    facts.skipped += 1
                    continue
                facts.documents_read += 1
                for doc in docs:
                    self._sweep(doc, facts)
                seen += 1
                if len(self.buffer) >= WRITE_BATCH:
                    self.flush()
                if self.on_progress is not None and seen % _PROGRESS_EVERY == 0:
                    self.on_progress(
                        f"{seen:,} of {facts.documents_total:,} responses read, "
                        f"{self.inventory.secrets:,} secrets"
                    )
        return True

    def _sweep(self, doc: Document, facts: CoverageFacts) -> None:
        facts.bytes_read += len(doc.text)
        if doc.truncated:
            facts.truncated += 1
        sweep = find(doc.text, now=self.started)
        for reason, n in sweep.dropped.items():
            facts.dropped[reason] = facts.dropped.get(reason, 0) + n
        facts.matches += len(sweep.matches)
        self.buffer.extend(observations_for(sweep, doc))


def _mine_locked(
    session: Session,
    *,
    scan_id: uuid.UUID,
    target_id: uuid.UUID,
    project_id: uuid.UUID,
    corpora: list[Corpus],
    incremental: bool,
    aborted: Callable[[], bool] | None,
    on_progress: Callable[[str], None] | None,
    announce: Callable[[], None] | None,
) -> MineOutcome:
    outcome = MineOutcome()
    inventory = SecretInventory(
        session,
        scan_id=scan_id,
        target_id=target_id,
        project_id=project_id,
        incremental=incremental,
    )
    miner = _Miner(
        session,
        inventory,
        scan_id=scan_id,
        aborted=aborted,
        on_progress=on_progress,
        announce=announce,
    )
    detectors = detector_count()
    done: list[CoverageFacts] = []
    for corpus in corpora:
        facts = CoverageFacts(
            source=corpus.source,
            status=CoverageStatus.COMPLETED.value,
            detectors=detectors,
            started_at=miner.started,
        )
        before = inventory.secrets
        try:
            completed = miner.read(corpus, facts)
            miner.flush()
        except Exception as exc:
            session.rollback()
            miner.buffer.clear()
            facts.status = CoverageStatus.FAILED.value
            facts.error = str(exc)[:2000]
            done.append(facts)
            _finish(inventory, done, outcome)
            raise
        facts.secrets = inventory.secrets - before
        done.append(facts)
        if not completed:
            outcome.aborted = True
            facts.status = CoverageStatus.PARTIAL.value
            facts.error = CANCELLED
            break
    _finish(inventory, done, outcome)
    return outcome


def _finish(
    inventory: SecretInventory, done: list[CoverageFacts], outcome: MineOutcome
) -> None:
    outcome.secrets = inventory.secrets
    for facts in done:
        outcome.absorb(facts)
        inventory.record_coverage(facts)


def stage_mined(session: Session, scan_id: uuid.UUID) -> bool:
    """Whether the stage recorded coverage for this scan."""
    return bool(
        session.scalar(
            select(SecretCoverage.id)
            .where(
                SecretCoverage.scan_id == scan_id,
                SecretCoverage.source.in_(STAGE_SOURCES),
            )
            .limit(1)
        )
    )


_PENDING = text(
    """
    SELECT s.id
      FROM scans s
     WHERE s.status = ANY(:statuses)
       AND s.scope = :scope
       AND (s.execution_config -> 'stages' -> 'secret_mining') IS NULL
       AND NOT EXISTS (SELECT 1 FROM secret_coverage c WHERE c.scan_id = s.id)
       AND (
             EXISTS (
               SELECT 1 FROM http_assets a
                WHERE a.scan_id = s.id
                  AND (a.response_body IS NOT NULL OR a.raw_response_header IS NOT NULL)
             )
             OR EXISTS (SELECT 1 FROM endpoint_responses r WHERE r.scan_id = s.id)
             OR EXISTS (
               SELECT 1 FROM vulnerabilities v
                WHERE v.scan_id = s.id AND v.response IS NOT NULL
             )
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
