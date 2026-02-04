from functools import lru_cache

from shared.config import BaseSettings_


class Settings(BaseSettings_):
    ###############################################################
    # Task Time Limits (seconds)
    ###############################################################
    TASK_SOFT_TIME_LIMIT: int = 3600 * 6  # 6 hours
    TASK_HARD_TIME_LIMIT: int = 3600 * 8  # 8 hours

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
