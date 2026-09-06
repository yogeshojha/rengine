from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

_server_settings = {"application_name": f"{settings.APP_NAME}-api"}

# reclaims any connection a request leaks inside an open transaction
if settings.DB_IDLE_TX_TIMEOUT > 0:
    _server_settings["idle_in_transaction_session_timeout"] = str(
        settings.DB_IDLE_TX_TIMEOUT * 1000
    )

engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
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
