import asyncio
import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.api.access import StreamAccess
from app.api.deps import (
    StreamUser,
    get_token_from_request,
    revoked_since_issue,
    token_still_valid,
)
from app.core.security import ISSUED_MS_CLAIM, decode_token
from shared.enums.sse import SSEChannel
from shared.logging import get_logger
from shared.services.project_access import ProjectSet, may_open
from shared.sse import STREAM_CLOSED, sse_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

HEARTBEAT_SECONDS = 30.0
UNAUTHORIZED = "event: unauthorized\ndata: {}\n\n"

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

CHANNEL_PATTERN = re.compile(
    rf"^({SSEChannel.PROJECT}:[a-f0-9\-]+|{SSEChannel.BROADCAST})$"
)


async def _closing(user_id: uuid.UUID, issued: object) -> str | None:
    """The frame that ends the stream, empty when it ends without one."""
    try:
        revoked = await revoked_since_issue(user_id, issued)
    except HTTPException:
        return ""
    return UNAUTHORIZED if revoked else None


def _opens(channel: str, access: ProjectSet) -> bool:
    if channel == SSEChannel.BROADCAST:
        return True
    try:
        project_id = uuid.UUID(channel.partition(":")[2])
    except ValueError:
        return False
    return may_open(access, project_id)


def validate_channels(requested: list[str], access: ProjectSet) -> list[str]:
    validated: list[str] = []

    for channel in requested:
        if not CHANNEL_PATTERN.match(channel):
            logger.warning("SSE channel rejected (malformed): %s", channel)
        elif not _opens(channel, access):
            logger.warning("SSE channel rejected (no access): %s", channel)
        else:
            validated.append(channel)

    return validated


@router.get("/stream")
async def event_stream(
    request: Request,
    current_user: StreamUser,
    token: Annotated[str, Depends(get_token_from_request)],
    access: StreamAccess,
    channels: str = Query(
        ...,
        description="Comma-separated channels",
        examples=["broadcast,project:proj-uuid"],
    ),
):
    requested = [ch.strip() for ch in channels.split(",") if ch.strip()]

    if not requested:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one channel is required.",
        )

    validated = validate_channels(requested, access)

    if not validated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No valid channels in request.",
        )

    if sse_manager.at_capacity():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Too many event streams.",
        )

    owner = str(current_user.id)
    if not sse_manager.claim(owner):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many event streams for this user.",
        )
    started = False

    def settle() -> None:
        if not started:
            sse_manager.release(owner)

    issued = (decode_token(token) or {}).get(ISSUED_MS_CLAIM)

    async def generate():
        nonlocal started
        loop = asyncio.get_running_loop()
        deadline = loop.time() + HEARTBEAT_SECONDS
        started = True
        async with sse_manager.stream(validated, owner, claimed=True) as queue:
            try:
                while True:
                    if await request.is_disconnected():
                        break

                    if loop.time() >= deadline:
                        try:
                            valid = await token_still_valid(token)
                        except HTTPException:
                            break
                        if not valid:
                            yield UNAUTHORIZED
                            break
                        deadline = loop.time() + HEARTBEAT_SECONDS

                    try:
                        message = await asyncio.wait_for(
                            queue.get(), timeout=deadline - loop.time()
                        )
                    except TimeoutError:
                        yield "event: heartbeat\ndata: {}\n\n"
                        continue
                    if message is STREAM_CLOSED:
                        break
                    closing = await _closing(current_user.id, issued)
                    if closing is not None:
                        if closing:
                            yield closing
                        break
                    yield message

            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
        background=BackgroundTask(settle),
    )
