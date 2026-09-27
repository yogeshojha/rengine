from functools import lru_cache

from shared.config import BaseAppSettings


class Settings(BaseAppSettings):
    @property
    def database_url(self) -> str:
        """Database URL for Worker (sync)."""
        return self.database_url_sync


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
