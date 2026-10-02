import asyncio
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import (
    StreamUser,
    get_token_from_request,
    token_still_valid,
)
from shared.enums.sse import SSEChannel
from shared.logging import get_logger
from shared.sse import STREAM_CLOSED, sse_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

HEARTBEAT_SECONDS = 30.0

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

CHANNEL_PATTERN = re.compile(
    rf"^({SSEChannel.PROJECT}:[a-f0-9\-]+|{SSEChannel.BROADCAST})$"
)


def validate_channels(requested: list[str]) -> list[str]:
    validated: list[str] = []

    for channel in requested:
        if CHANNEL_PATTERN.match(channel):
            validated.append(channel)
        else:
            logger.warning("SSE channel rejected (malformed): %s", channel)

    return validated


@router.get("/stream")
async def event_stream(
    request: Request,
    _current_user: StreamUser,
    token: Annotated[str, Depends(get_token_from_request)],
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
            detail="At least one channel is required",
        )

    validated = validate_channels(requested)

    if not validated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No valid channels in request",
        )

    if sse_manager.at_capacity():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Too many event streams",
        )

    async def generate():
        async with sse_manager.stream(validated) as queue:
            try:
                while True:
                    if await request.is_disconnected():
                        break

                    try:
                        message = await asyncio.wait_for(
                            queue.get(), timeout=HEARTBEAT_SECONDS
                        )
                        if message is STREAM_CLOSED:
                            break
                        yield message
                    except TimeoutError:
                        if not await token_still_valid(token):
                            yield "event: unauthorized\ndata: {}\n\n"
                            break
                        yield ": heartbeat\n\n"

            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        generate(), media_type="text/event-stream", headers=STREAM_HEADERS
    )
