from shared.config import BaseAppSettings


class Settings(BaseAppSettings):
    @property
    def database_url(self) -> str:
        """Database URL for Worker (sync)."""
        return self.database_url_sync


settings = Settings()
