"""
Unified SSE stream endpoint.

Clients connect with:
    GET /events/stream?channels=broadcast,project:{project_id}
"""

import asyncio
import logging
import re

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser
from app.core.sse import sse_manager
from shared.enums.sse import SSEChannel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])

# Valid channel patterns - derived from SSEChannel enum
CHANNEL_PATTERN = re.compile(
    rf"^({SSEChannel.PROJECT}:[a-f0-9\-]+|{SSEChannel.BROADCAST})$"
)


def validate_channels(requested: list[str]) -> list[str]:
    """Validate channel subscriptions.

    Rules:
      - project:{id}  -> project-scoped events (activities, scans)
      - broadcast      -> system-wide notifications and announcements
      - anything else  -> silently rejected
    """
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
    _current_user: CurrentUser,
    channels: str = Query(
        ...,
        description="Comma-separated list of channels to subscribe to",
        examples=["broadcast,project:proj-uuid"],
    ),
):
    """Server-Sent Events stream with channel-based filtering.
    The client specifies which channels to subscribe to via query parameter.

    Channel types:
      - ``project:{project_id}`` — project events (activities, scans, etc.)
      - ``broadcast`` — system-wide notifications and announcements
    """
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
            detail="No authorized channels in request",
        )

    async def generate():
        async with sse_manager.stream(validated) as queue:
            try:
                while True:
                    if await request.is_disconnected():
                        break

                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield message
                    except TimeoutError:
                        # SSE keepalive — browsers close idle connections
                        yield ": heartbeat\n\n"

            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def sse_health(
    _current_user: CurrentUser,
):
    """Diagnostic endpoint for SSE connection state."""
    return {
        "status": "healthy",
        "active_connections": sse_manager.get_active_connections(),
        "channels": sse_manager.get_channel_stats(),
    }
