import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_UNSAFE_IN_ARGV = re.compile(r"[\s\"'\\]")
PUBLISHED_SECRET_KEY = "change-me-in-production-use-openssl-rand-hex-32"  # noqa: S105
SECRET_KEY_MIN_LENGTH = 32
_VERSION_FILE = Path(__file__).resolve().parents[1] / "VERSION"


def _release() -> str:
    try:
        return _VERSION_FILE.read_text().strip() or "unknown"
    except OSError:
        return "unknown"


APP_NAME = "reNgine"
APP_VERSION = _release()


class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    DEBUG: bool = False
    SQL_ECHO: bool = False

    LOG_LEVEL: str = "INFO"

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    SECRET_KEY: str = ""

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
    CELERY_SCAN_CONCURRENCY: int = 16
    CELERY_CONTROL_CONCURRENCY: int = 8
    CELERY_DEFAULT_CONCURRENCY: int = 4
    TASK_SOFT_TIME_LIMIT: int = 3600 * 6
    TASK_HARD_TIME_LIMIT: int = 3600 * 8

    @property
    def ui_base_url(self) -> str:
        return (
            self.CORS_ORIGINS[0] if self.CORS_ORIGINS else "http://localhost:5173"
        ).rstrip("/")

    @property
    def worker_children(self) -> int:
        return (
            self.CELERY_SCAN_CONCURRENCY
            + self.CELERY_CONTROL_CONCURRENCY
            + self.CELERY_DEFAULT_CONCURRENCY
        )

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

    # cached aggregates, on an instance that evicts
    REDIS_CACHE_HOST: str = "cache"
    REDIS_CACHE_PORT: int = 6379

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

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        if not v or info.data.get("DEBUG", False):
            return v
        if v == PUBLISHED_SECRET_KEY or len(v) < SECRET_KEY_MIN_LENGTH:
            msg = (
                f"SECRET_KEY must be a generated value of at least "
                f"{SECRET_KEY_MIN_LENGTH} characters. "
                "Generate one with: openssl rand -hex 32"
            )
            raise ValueError(msg)
        return v

    def _redis_credentials(self) -> str:
        return f":{quote(self.REDIS_PASSWORD, safe='')}@" if self.REDIS_PASSWORD else ""

    def _redis_url(self, db: int) -> str:
        return (
            f"redis://{self._redis_credentials()}"
            f"{self.REDIS_HOST}:{self.REDIS_PORT}/{db}"
        )

    @property
    def redis_url(self) -> str:
        return self._redis_url(self.REDIS_DB)

    @property
    def redis_cache_url(self) -> str:
        return (
            f"redis://{self._redis_credentials()}"
            f"{self.REDIS_CACHE_HOST}:{self.REDIS_CACHE_PORT}/0"
        )

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self._redis_url(self.REDIS_DB + 1)


@lru_cache(maxsize=1)
def base_settings() -> BaseAppSettings:
    return BaseAppSettings()
