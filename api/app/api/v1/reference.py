from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool

from app.api.deps import CurrentUser
from app.services.api_reference import reference
from shared.models.reference import ReferenceGroup

router = APIRouter(tags=["reference"])


@router.get("/reference", response_model=list[ReferenceGroup])
async def api_reference(_user: CurrentUser, request: Request):
    return await run_in_threadpool(reference, request.app)
