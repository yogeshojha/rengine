"""The only writer of secrets, secret_sightings and secret_coverage."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from shared.definitions.secrets import MAX_SIGHTINGS_PER_SECRET
from shared.models.secret import Secret, SecretCoverage, SecretSighting
from shared.utils.datetime import utc_now


@dataclass(frozen=True)
class Observation:
    fingerprint: str
    kind: str
    group: str
    vendor: str
    state: str
    is_secret: bool
    value: str
    subject: str | None
    meta: dict
    host: str
    url: str
    http_asset_id: uuid.UUID | None
    source: str
    offset: int
    context: str


@dataclass
class CoverageFacts:
    source: str
    status: str
    documents_total: int = 0
    documents_read: int = 0
    bytes_read: int = 0
    truncated: int = 0
    skipped: int = 0
    detectors: int = 0
    matches: int = 0
    secrets: int = 0
    dropped: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    started_at: datetime = field(default_factory=utc_now)


def _sighting_values(row: SecretSighting) -> dict:
    return {
        "id": row.id,
        "secret_id": row.secret_id,
        "scan_id": row.scan_id,
        "target_id": row.target_id,
        "project_id": row.project_id,
        "host": row.host,
        "url": row.url,
        "http_asset_id": row.http_asset_id,
        "source": row.source,
        "offset": row.offset,
        "context": row.context,
        "created_at": row.created_at,
    }


class SecretInventory:
    def __init__(
        self,
        session: Session,
        *,
        scan_id: uuid.UUID,
        target_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        self.session = session
        self.scan_id = scan_id
        self.target_id = target_id
        self.project_id = project_id
        self._ids: dict[str, uuid.UUID] = {}
        self._hosts: dict[str, set[str]] = {}
        self._sightings: dict[str, int] = {}
        self._seen: set[tuple[str, str, str]] = set()
        self._cleared = False
        self.secrets = 0
        self.sightings = 0

    def _clear(self) -> None:
        self.session.execute(delete(Secret).where(Secret.scan_id == self.scan_id))
        self.session.execute(
            delete(SecretCoverage).where(SecretCoverage.scan_id == self.scan_id)
        )
        self._cleared = True

    def write(self, observations: Iterable[Observation]) -> int:
        """Insert what is new, count what is not, and commit."""
        if not self._cleared:
            self._clear()
        rows: list[Secret] = []
        sightings: list[SecretSighting] = []
        touched: set[str] = set()
        for obs in observations:
            key = (obs.fingerprint, obs.url, obs.source)
            if key in self._seen:
                continue
            self._seen.add(key)
            secret_id = self._ids.get(obs.fingerprint)
            if secret_id is None:
                row = Secret(
                    scan_id=self.scan_id,
                    target_id=self.target_id,
                    project_id=self.project_id,
                    fingerprint=obs.fingerprint,
                    kind=obs.kind,
                    group=obs.group,
                    vendor=obs.vendor,
                    state=obs.state,
                    is_secret=obs.is_secret,
                    value=obs.value,
                    subject=obs.subject,
                    meta=obs.meta,
                    host=obs.host,
                    url=obs.url,
                    http_asset_id=obs.http_asset_id,
                    source=obs.source,
                    context=obs.context,
                )
                secret_id = row.id
                rows.append(row)
                self._ids[obs.fingerprint] = secret_id
                self._hosts[obs.fingerprint] = set()
                self._sightings[obs.fingerprint] = 0
            self._hosts[obs.fingerprint].add(obs.host)
            self._sightings[obs.fingerprint] += 1
            touched.add(obs.fingerprint)
            if self._sightings[obs.fingerprint] > MAX_SIGHTINGS_PER_SECRET:
                continue
            sightings.append(
                SecretSighting(
                    secret_id=secret_id,
                    scan_id=self.scan_id,
                    target_id=self.target_id,
                    project_id=self.project_id,
                    host=obs.host,
                    url=obs.url,
                    http_asset_id=obs.http_asset_id,
                    source=obs.source,
                    offset=obs.offset,
                    context=obs.context,
                )
            )
        if rows:
            self.session.add_all(sorted(rows, key=lambda r: r.fingerprint))
            self.session.flush()
        if sightings:
            self.session.execute(
                pg_insert(SecretSighting)
                .values([_sighting_values(row) for row in sightings])
                .on_conflict_do_nothing(constraint="uq_sighting_secret_url")
            )
        for fp in touched:
            self.session.execute(
                update(Secret)
                .where(Secret.id == self._ids[fp])
                .values(sightings=self._sightings[fp], hosts=len(self._hosts[fp]))
            )
        self.session.commit()
        for obj in rows:
            if obj in self.session:
                self.session.expunge(obj)
        self.secrets += len(rows)
        self.sightings += len(sightings)
        return len(rows)

    def record_coverage(self, facts: CoverageFacts) -> None:
        if not self._cleared:
            self._clear()
        ended = utc_now()
        self.session.execute(
            delete(SecretCoverage).where(
                SecretCoverage.scan_id == self.scan_id,
                SecretCoverage.source == facts.source,
            )
        )
        self.session.add(
            SecretCoverage(
                scan_id=self.scan_id,
                target_id=self.target_id,
                project_id=self.project_id,
                source=facts.source,
                status=facts.status,
                documents_total=facts.documents_total,
                documents_read=facts.documents_read,
                bytes_read=facts.bytes_read,
                truncated=facts.truncated,
                skipped=facts.skipped,
                detectors=facts.detectors,
                matches=facts.matches,
                secrets=facts.secrets,
                dropped=dict(facts.dropped),
                error=facts.error,
                started_at=facts.started_at,
                ended_at=ended,
                duration_seconds=(ended - facts.started_at).total_seconds(),
            )
        )
        self.session.commit()
