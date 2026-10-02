from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from shared.config import APP_NAME
from shared.definitions.channels import POOL_OVERFLOW as CHANNELS_POOL_OVERFLOW
from shared.definitions.channels import POOL_SIZE as CHANNELS_POOL_SIZE
from shared.logging import get_logger

logger = get_logger(__name__)

_server_settings = {"application_name": f"{APP_NAME}-api"}

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


def pool_demand() -> int:
    """Connections every pool can ask for at once."""
    per_child = settings.WORKER_DB_POOL_SIZE + settings.WORKER_DB_MAX_OVERFLOW
    api_pool = settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW
    api_processes = 1 if settings.API_RELOAD else settings.API_WORKERS
    return (
        api_processes * api_pool
        + CHANNELS_POOL_SIZE
        + CHANNELS_POOL_OVERFLOW
        + settings.worker_children * per_child
        + per_child
    )


async def check_capacity() -> None:
    """Warn when pool demand exceeds max_connections."""
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
