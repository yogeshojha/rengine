"""
Shared configuration settings for reNgine, used by both API and Worker components.
"""

from pydantic_settings import BaseSettings


class BaseSettings_(BaseSettings):
    ###############################################################
    # Application Settings
    ###############################################################
    APP_NAME: str = "reNgine"
    DEBUG: bool = False
    APP_VERSION: str = "3.0.0"

    ###############################################################
    # Logging Settings
    ###############################################################
    LOG_LEVEL: str = "INFO"

    ###############################################################
    # Database Settings
    ###############################################################
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "rengine"
    POSTGRES_PASSWORD: str = "rengine"
    POSTGRES_DB: str = "rengine"

    @property
    def database_url_async(self) -> str:
        """Async database URL for API (asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync database URL for Worker (psycopg2)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    ###############################################################
    # Redis Settings
    ###############################################################
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    ###############################################################
    # Celery Settings (shared)
    ###############################################################
    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
