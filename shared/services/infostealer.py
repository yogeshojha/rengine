"""Infostealer reports per target: the lookup domain, storage and the hosts they name."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shared.definitions.domains import registrable_domain
from shared.definitions.infostealer import (
    DAILY_AFTER,
    MAX_CHANGE_HOSTS,
    MAX_ERROR_LENGTH,
    STALE_AFTER,
)
from shared.enums.target import TargetType
from shared.enums.task_status import TaskStatus
from shared.models.infostealer import (
    InfostealerChange,
    InfostealerLogin,
    InfostealerSighting,
    TargetInfostealer,
)
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings
from shared.models.target import Target
from shared.utils.datetime import utc_now
from shared.utils.validation import dns_lookup_name
from tools.hudsonrock.models import InfostealerReport


def lookup_domain(value: str, target_type: TargetType) -> str | None:
    """The registrable domain a target is looked up under, or None when it has none."""
    host = dns_lookup_name(value, target_type)
    return (registrable_domain(host) or None) if host else None


def lookups_enabled(session: Session | None) -> bool:
    if session is None:
        return False
    value = session.scalar(
        select(InstanceSettings.infostealer_lookups).where(
            InstanceSettings.singleton_key == SINGLETON_KEY
        )
    )
    return True if value is None else bool(value)


def stored(session: Session, target_id: UUID) -> TargetInfostealer | None:
    return session.scalar(
        select(TargetInfostealer).where(TargetInfostealer.target_id == target_id)
    )


def is_stale(record: TargetInfostealer | None) -> bool:
    return record is None or utc_now() - record.checked_at > STALE_AFTER


def mark(target: Target, status: TaskStatus, error: str | None = None) -> None:
    target.infostealer_status = status
    target.infostealer_error = error[:MAX_ERROR_LENGTH] if error else None
    target.updated_at = utc_now()


def due(record: TargetInfostealer | None) -> bool:
    """Whether a daily check reads the report again."""
    return record is None or utc_now() - record.checked_at > DAILY_AFTER


def _risen(
    session: Session, target_id: UUID, report: InfostealerReport, now, *, first: bool
) -> list[dict]:
    """Hosts listed for the first time or above their highest count, sightings updated."""
    totals: dict[tuple[str, str], int] = {}
    for login in report.logins:
        key = (login.audience, login.host)
        totals[key] = totals.get(key, 0) + login.credentials
    seen = {
        (s.audience, s.host): s
        for s in session.scalars(
            select(InfostealerSighting).where(
                InfostealerSighting.target_id == target_id
            )
        )
    }
    risen: list[dict] = []
    for (audience, host), credentials in totals.items():
        sighting = seen.get((audience, host))
        if sighting is None:
            session.add(
                InfostealerSighting(
                    target_id=target_id,
                    audience=audience,
                    host=host,
                    first_seen=now,
                    credentials_peak=credentials,
                )
            )
            before = 0
        elif credentials > sighting.credentials_peak:
            before = sighting.credentials_peak
            sighting.credentials_peak = credentials
        else:
            continue
        if not first:
            risen.append(
                {
                    "audience": audience,
                    "host": host,
                    "credentials_from": before,
                    "credentials_to": credentials,
                    "new": sighting is None,
                }
            )
    risen.sort(key=lambda r: (r["audience"], -r["credentials_to"], r["host"]))
    return risen


def store(
    session: Session, target_id: UUID, report: InfostealerReport
) -> InfostealerChange | None:
    """Replace the target's report and its logins. Returns what the lookup added."""
    now = utc_now()
    record = stored(session, target_id)
    first = record is None
    if record is None:
        record = TargetInfostealer(target_id=target_id, domain=report.domain)
    previous_checked_at = None if first else record.checked_at
    employees_peak = report.employees if first else record.employees_peak
    users_peak = report.users if first else record.users_peak
    record.domain = report.domain
    record.checked_at = now
    record.total = report.total
    record.employees = report.employees
    record.users = report.users
    record.third_parties = report.third_parties
    record.total_urls = report.total_urls
    record.last_employee_at = report.last_employee_at
    record.last_user_at = report.last_user_at
    record.employees_peak = max(employees_peak, report.employees)
    record.users_peak = max(users_peak, report.users)
    record.families = [f.model_dump() for f in report.families]
    record.passwords = report.passwords
    record.applications = [a.model_dump() for a in report.applications]
    record.services = [s.model_dump() for s in report.services]
    session.add(record)
    session.execute(
        delete(InfostealerLogin).where(InfostealerLogin.target_id == target_id)
    )
    session.add_all(
        InfostealerLogin(
            target_id=target_id,
            audience=login.audience,
            host=login.host,
            scheme=login.scheme,
            port=login.port,
            path=login.path,
            credentials=login.credentials,
        )
        for login in report.logins
    )
    risen = _risen(session, target_id, report, now, first=first)
    rose = report.employees > employees_peak or report.users > users_peak
    if first or not (rose or risen):
        return None
    change = InfostealerChange(
        target_id=target_id,
        checked_at=now,
        previous_checked_at=previous_checked_at,
        employees_from=employees_peak,
        employees_to=record.employees_peak,
        users_from=users_peak,
        users_to=record.users_peak,
        hosts=risen[:MAX_CHANGE_HOSTS],
    )
    session.add(change)
    return change


def hosts(session: Session, target_id: UUID) -> set[str]:
    """Every host the target's report lists a login on."""
    return set(
        session.scalars(
            select(InfostealerLogin.host)
            .where(InfostealerLogin.target_id == target_id)
            .distinct()
        )
    )


def group_by_domain(
    targets: Iterable[Target],
) -> tuple[dict[str, list[Target]], list[Target]]:
    """Targets keyed by lookup domain, and the targets that have none."""
    groups: dict[str, list[Target]] = {}
    none: list[Target] = []
    for target in targets:
        domain = lookup_domain(target.target_value, target.target_type)
        if domain is None:
            none.append(target)
        else:
            groups.setdefault(domain, []).append(target)
    return groups, none
