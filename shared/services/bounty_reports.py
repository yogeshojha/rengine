"""The account's own reports and bounties, stored as the platform states them."""

from __future__ import annotations

from sqlalchemy import String, any_, delete, not_, select
from sqlalchemy.dialects.postgresql import array, insert
from sqlalchemy.orm import Session
from sqlmodel import col

from shared.definitions.bounty_programs import SYNC_INTERVAL_HOURS
from shared.definitions.mode_features import CAP_BOUNTY_PROGRAMS, has_capability
from shared.models.bounty_report import BountyAccount, BountyAward, BountyReport
from shared.models.instance_settings import InstanceSettings
from shared.services.bounty_programs import sync_settings
from shared.services.bounty_providers import BountyProvider, BountyProviderError
from shared.utils.datetime import utc_now

MAX_ERROR = 500
INSERT_BATCH = 1000


def _replace(session: Session, model, platform: str, rows: list[dict]) -> int:
    """Upsert by the platform's id and drop what the platform no longer lists."""
    now = utc_now()
    ids = sorted({r["external_id"] for r in rows})
    by_id = {r["external_id"]: r for r in rows}
    for start in range(0, len(ids), INSERT_BATCH):
        values = [
            {**by_id[i], "platform": platform, "synced_at": now}
            for i in ids[start : start + INSERT_BATCH]
        ]
        stmt = insert(model).values(values)
        updated = {
            k: stmt.excluded[k]
            for k in values[0]
            if k not in {"platform", "external_id"}
        }
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=["platform", "external_id"], set_=updated
            )
        )
    session.execute(
        delete(model).where(
            model.platform == platform,
            not_(col(model.external_id) == any_(array(ids or [""], type_=String))),
        )
    )
    return len(ids)


def _account(session: Session, platform: str) -> BountyAccount:
    row = session.get(BountyAccount, platform)
    if row is None:
        row = BountyAccount(platform=platform)
        session.add(row)
    return row


def sync_reports(session: Session, provider: BountyProvider) -> dict[str, int] | None:
    """One platform's reports and bounties. None when the platform has no such read."""
    try:
        fetched = provider.own_reports()
    except BountyProviderError as exc:
        session.rollback()
        account = _account(session, provider.platform)
        account.error = str(exc)[:MAX_ERROR]
        session.commit()
        raise
    if fetched is None:
        return None
    reports = _replace(session, BountyReport, provider.platform, fetched.reports)
    awards = _replace(session, BountyAward, provider.platform, fetched.awards)
    account = _account(session, provider.platform)
    for key in ("username", "reputation", "signal", "impact"):
        setattr(account, key, fetched.account.get(key))
    account.synced_at = utc_now()
    account.error = None
    session.commit()
    return {"reports": reports, "awards": awards}


def reports_enabled(session: Session) -> bool:
    """Bug bounty mode with a sync schedule that is not off."""
    mode = session.scalar(select(InstanceSettings.mode).limit(1))
    interval, _ = sync_settings(session)
    return has_capability(mode, CAP_BOUNTY_PROGRAMS) and interval in SYNC_INTERVAL_HOURS
