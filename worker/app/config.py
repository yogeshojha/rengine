from functools import lru_cache

from shared.config import BaseAppSettings


class Settings(BaseAppSettings):
    ###############################################################
    # Task Time Limits (seconds)
    ###############################################################
    TASK_SOFT_TIME_LIMIT: int = 3600 * 6  # 6 hours
    TASK_HARD_TIME_LIMIT: int = 3600 * 8  # 8 hours

    ###############################################################
    # Database pool (per prefork child, not per worker process)
    ###############################################################
    WORKER_DB_POOL_SIZE: int = 2
    WORKER_DB_MAX_OVERFLOW: int = 3
    WORKER_DB_POOL_TIMEOUT: int = 30

    ###############################################################
    # Convenience Properties
    ###############################################################
    @property
    def database_url(self) -> str:
        """Database URL for Worker (sync)."""
        return self.database_url_sync


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
