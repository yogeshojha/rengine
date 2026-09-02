from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    APP_NAME: str = "reNgine"
    DEBUG: bool = False
    APP_VERSION: str = "3.0.0"

    LOG_LEVEL: str = "INFO"

    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "rengine"
    POSTGRES_PASSWORD: str = "rengine"  # noqa: S105
    POSTGRES_DB: str = "rengine"

    @property
    def database_url_async(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        # the scan canvas chains groups, which celery runs as chords — those need a backend
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB + 1}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
