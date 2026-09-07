"""Refresh the bug bounty program list and every program's structured scope."""

from celery import shared_task
from sqlalchemy import select

from app.database import get_sync_session
from shared.definitions.bounty_programs import BountyPlatform
from shared.logging import get_logger
from shared.models.bounty_program import BountyProgram
from shared.services.bounty_programs import (
    CredentialsError,
    HackerOneError,
    credentials,
    sync_programs,
    sync_scopes,
)

logger = get_logger(__name__)

SCOPE_FAILURE_BUDGET = 25


@shared_task(name="app.tasks.bounty_programs.sync")
def sync(scopes: bool = True) -> dict:
    """Pull programs, then each program's scope so the library can be filtered by it."""
    with get_sync_session() as session:
        auth = credentials(session)
        if not auth:
            logger.info("bounty program sync skipped, no hackerone credentials")
            return {"skipped": "not_configured"}
        try:
            result = sync_programs(session, auth)
        except CredentialsError as exc:
            logger.warning("bounty program sync rejected", error=str(exc))
            return {"error": str(exc)}
        except HackerOneError as exc:
            logger.warning("bounty program sync failed", error=str(exc))
            return {"error": str(exc)}

        if not scopes:
            return result

        programs = (
            session.execute(
                select(BountyProgram).where(
                    BountyProgram.platform == BountyPlatform.HACKERONE.value
                )
            )
            .scalars()
            .all()
        )
        assets = 0
        failed = 0
        for program in programs:
            try:
                assets += sync_scopes(session, program, auth)
            except CredentialsError as exc:
                logger.warning("bounty scope sync rejected", error=str(exc))
                break
            except HackerOneError as exc:
                failed += 1
                logger.info(
                    "bounty scope sync failed", handle=program.handle, error=str(exc)
                )
                # a run of failures means the API is unhappy, not this one program
                if failed >= SCOPE_FAILURE_BUDGET:
                    logger.warning("bounty scope sync abandoned", failed=failed)
                    break
        return {**result, "assets": assets, "scope_failures": failed}


@shared_task(name="app.tasks.bounty_programs.sync_program")
def sync_program(handle: str) -> dict:
    """Refresh one program's scope, for a program opened before the sweep reached it."""
    with get_sync_session() as session:
        auth = credentials(session)
        if not auth:
            return {"skipped": "not_configured"}
        program = session.execute(
            select(BountyProgram).where(
                BountyProgram.platform == BountyPlatform.HACKERONE.value,
                BountyProgram.handle == handle,
            )
        ).scalar_one_or_none()
        if not program:
            return {"error": "unknown program"}
        try:
            return {"assets": sync_scopes(session, program, auth)}
        except HackerOneError as exc:
            logger.info("bounty scope sync failed", handle=handle, error=str(exc))
            return {"error": str(exc)}
