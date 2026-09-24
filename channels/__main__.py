"""Run every remote control channel that is switched on."""

from __future__ import annotations

import asyncio
import contextlib
import signal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from channels.telegram.listener import DISPATCH_SLOTS, TelegramListener
from shared.logging import get_logger

logger = get_logger(__name__)

POOL_SIZE = DISPATCH_SLOTS + 2
POOL_OVERFLOW = 2


async def _serve() -> None:
    from app.config import settings  # noqa: PLC0415

    engine = create_async_engine(
        settings.database_url,
        pool_size=POOL_SIZE,
        max_overflow=POOL_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        connect_args={"server_settings": {"application_name": "reNgine-channels"}},
    )
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    ui_base = (
        settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
    )

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    logger.info("remote control channels starting")
    try:
        await TelegramListener(sessions, ui_base).run(stop)
    finally:
        await engine.dispose()
        logger.info("remote control channels stopped")


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_serve())


if __name__ == "__main__":
    main()
