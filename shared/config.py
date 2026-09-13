import re
from functools import lru_cache
from urllib.parse import quote

from pydantic import field_validator
from pydantic_settings import BaseSettings

_UNSAFE_IN_ARGV = re.compile(r"[\s\"'\\]")


class BaseAppSettings(BaseSettings):
    APP_NAME: str = "reNgine"
    DEBUG: bool = False
    SQL_ECHO: bool = False
    APP_VERSION: str = "3.0.0"

    LOG_LEVEL: str = "INFO"

    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "rengine"
    POSTGRES_PASSWORD: str = "rengine"  # noqa: S105
    POSTGRES_DB: str = "rengine"

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 10
    DB_POOL_RECYCLE: int = 1800
    DB_IDLE_TX_TIMEOUT: int = 120

    WORKER_DB_POOL_SIZE: int = 2
    WORKER_DB_MAX_OVERFLOW: int = 3
    WORKER_DB_POOL_TIMEOUT: int = 30
    CELERY_SCAN_CONCURRENCY: int = 12

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

    # every outbound call that is not scan traffic: intel feeds, RDAP, RIPEstat
    EGRESS_PROXY_URL: str = ""
    EGRESS_TIMEOUT: float = 30.0
    EGRESS_USER_AGENT: str = (
        "Mozilla/5.0 (compatible; reNgine/3.0; +https://github.com/yogeshojha/rengine)"
    )

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @field_validator("REDIS_PASSWORD")
    @classmethod
    def validate_redis_password(cls, v: str) -> str:
        if _UNSAFE_IN_ARGV.search(v):
            msg = (
                "REDIS_PASSWORD must not contain whitespace, quotes or backslashes. "
                "Generate one with: openssl rand -hex 32"
            )
            raise ValueError(msg)
        return v

    def _redis_url(self, db: int) -> str:
        credentials = (
            f":{quote(self.REDIS_PASSWORD, safe='')}@" if self.REDIS_PASSWORD else ""
        )
        return f"redis://{credentials}{self.REDIS_HOST}:{self.REDIS_PORT}/{db}"

    @property
    def redis_url(self) -> str:
        return self._redis_url(self.REDIS_DB)

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self._redis_url(self.REDIS_DB + 1)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache(maxsize=1)
def base_settings() -> BaseAppSettings:
    return BaseAppSettings()
