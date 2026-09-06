"""Sync database session for Celery workers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# each prefork child inherits this engine and is single-threaded, so the pool is
# sized per child: concurrency x (pool_size + max_overflow) shares max_connections
engine = create_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=settings.WORKER_DB_POOL_SIZE,
    max_overflow=settings.WORKER_DB_MAX_OVERFLOW,
    pool_timeout=settings.WORKER_DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    connect_args={"application_name": f"{settings.APP_NAME}-worker"},
)

SyncSessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)


def get_sync_session() -> Session:
    return SyncSessionLocal()
