from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)

_server_settings = {"application_name": f"{settings.APP_NAME}-api"}

if settings.DB_IDLE_TX_TIMEOUT > 0:
    _server_settings["idle_in_transaction_session_timeout"] = str(
        settings.DB_IDLE_TX_TIMEOUT * 1000
    )

engine = create_async_engine(
    settings.database_url,
    echo=settings.SQL_ECHO,
    future=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={"server_settings": _server_settings},
)

async_db_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    async with async_db_session() as session:
        yield session


def pool_stats() -> dict[str, int]:
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_out": pool.checkedout(),
        "checked_in": pool.checkedin(),
        "overflow": pool.overflow(),
        "capacity": settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW,
    }


def pool_demand() -> int:
    """Connections every pool can ask for at once."""
    per_child = settings.WORKER_DB_POOL_SIZE + settings.WORKER_DB_MAX_OVERFLOW
    return (
        settings.DB_POOL_SIZE
        + settings.DB_MAX_OVERFLOW
        + settings.CELERY_SCAN_CONCURRENCY * per_child
        + per_child
    )


async def check_capacity() -> None:
    """Say out loud when the pools can outgrow the server."""
    demand = pool_demand()
    try:
        async with engine.connect() as conn:
            allowed = int(await conn.scalar(text("SHOW max_connections")))
            reserved = int(
                await conn.scalar(text("SHOW superuser_reserved_connections"))
            )
    except Exception:
        logger.debug("could not read the connection ceiling", exc_info=True)
        return
    usable = allowed - reserved
    if demand > usable:
        logger.warning(
            "database pools can outgrow the server",
            demand=demand,
            usable=usable,
            hint="raise POSTGRES_MAX_CONNECTIONS or lower the pool sizes",
        )
    else:
        logger.info("database pool headroom", demand=demand, usable=usable)
