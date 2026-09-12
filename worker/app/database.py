"""Sync database session for Celery workers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    echo=settings.SQL_ECHO,
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
