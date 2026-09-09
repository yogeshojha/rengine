import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.database import get_session
from shared.definitions.toolbox import (
    INPUT_LABELS,
    LookupRequest,
    LookupResult,
    RunStatus,
    ToolboxCatalog,
    ToolRunRead,
    ToolRunRequest,
)
from shared.logging import get_logger
from shared.models.user import User
from shared.services.celery_dispatch import dispatch_toolbox_run
from toolbox import registry, store
from toolbox.base import ToolContext, ToolError
from toolbox.registry import ToolSpec
from toolbox.routing import classify
from toolbox.runner import complete, expire, fail, validate

logger = get_logger(__name__)

router = APIRouter(prefix="/toolbox", tags=["toolbox"])

INLINE_TIMEOUT = 45
UNRECOGNISED = (
    "Enter a domain, IP address, address range, URL, autonomous system or CVE."
)


@router.get("/catalog", response_model=ToolboxCatalog)
async def toolbox_catalog(_current_user: CurrentUser):
    return registry.catalog()


@router.get("/runs", response_model=list[ToolRunRead])
async def toolbox_runs(current_user: CurrentUser):
    return [expire(run) for run in await store.recent(current_user.id)]


@router.get("/runs/{run_id}", response_model=ToolRunRead)
async def toolbox_run(
    current_user: CurrentUser,
    run_id: Annotated[str, Path()],
):
    run = await store.get(current_user.id, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That run has expired."
        )
    before = run.status
    expire(run)
    if run.status != before:
        await store.save(current_user.id, run)
    return run


@router.delete("/runs", status_code=status.HTTP_204_NO_CONTENT)
async def clear_toolbox_runs(current_user: CurrentUser):
    await store.clear(current_user.id)


@router.post("/lookup", response_model=LookupResult)
async def lookup_value(
    body: LookupRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Classify a raw value and run every tool that answers it without being asked."""
    classified = classify(body.q)
    if classified is None:
        return LookupResult(value=body.q.strip(), error=UNRECOGNISED)

    kind, value = classified
    specs = registry.for_kind(kind)
    if not specs:
        return LookupResult(
            kind=kind,
            kind_label=INPUT_LABELS.get(kind),
            value=value,
            error=f"No tool handles a {INPUT_LABELS.get(kind, kind).lower()}.",
        )

    await _check_rate(current_user)
    project_id = _project_id(body.project_id)
    ctx = ToolContext(session=session, user_id=current_user.id, project_id=project_id)

    runs: list[ToolRunRead] = []
    offered: list[str] = []
    for spec in specs:
        if not spec.auto:
            offered.append(spec.name)
            continue
        runs.append(
            await _start(spec, spec.tool_cls.payload_for(value), ctx, current_user)
        )

    return LookupResult(
        kind=kind,
        kind_label=INPUT_LABELS.get(kind),
        value=value,
        runs=runs,
        offered=offered,
    )


@router.post("/run", response_model=ToolRunRead)
async def run_tool(
    body: ToolRunRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    spec = registry.get(body.tool)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tool called {body.tool!r}.",
        )
    await _check_rate(current_user)
    ctx = ToolContext(
        session=session,
        user_id=current_user.id,
        project_id=_project_id(body.project_id),
    )
    return await _start(spec, body.input, ctx, current_user)


async def _start(
    spec: ToolSpec, payload: dict, ctx: ToolContext, current_user: User
) -> ToolRunRead:
    try:
        args = validate(spec, payload)
    except ToolError as exc:
        rejected = store.new_run(
            tool=spec.name,
            title=spec.title,
            label=_first_value(payload) or spec.title,
            payload=payload,
            status=RunStatus.FAILED.value,
        )
        fail(rejected, str(exc))
        await store.save(current_user.id, rejected)
        return rejected

    run = store.new_run(
        tool=spec.name,
        title=spec.title,
        label=spec.tool_cls.label_for(args),
        payload=args.model_dump(mode="json"),
        status=RunStatus.QUEUED.value,
    )

    if spec.queued:
        await store.save(current_user.id, run)
        accepted = dispatch_toolbox_run(
            run_id=run.id,
            user_id=str(current_user.id),
            tool=spec.name,
            payload=run.input,
            project_id=str(ctx.project_id) if ctx.project_id else None,
        )
        if not accepted:
            fail(run, "The task queue did not accept the run.")
            await store.save(current_user.id, run)
        return run

    run.status = RunStatus.RUNNING.value
    try:
        outcome = await asyncio.wait_for(
            spec.tool_cls().run(ctx, args), timeout=INLINE_TIMEOUT
        )
        complete(run, outcome)
    except TimeoutError:
        fail(run, f"The lookup did not answer within {INLINE_TIMEOUT} seconds.")
    except ToolError as exc:
        fail(run, str(exc))
    except Exception as exc:
        logger.warning("toolbox run failed", tool=spec.name, error=str(exc))
        fail(run, f"The lookup failed: {exc}")

    await store.save(current_user.id, run)
    return run


async def _check_rate(current_user: User) -> None:
    if not await store.within_rate(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many toolbox runs. Try again in a minute.",
        )


def _first_value(payload: dict) -> str:
    return next(
        (v.strip() for v in payload.values() if isinstance(v, str) and v.strip()), ""
    )


def _project_id(raw: str | None) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None
