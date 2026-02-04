from functools import lru_cache

from pydantic import field_validator

from shared.config import BaseSettings_


class Settings(BaseSettings_):
    ###############################################################
    # API-Specific Settings
    ###############################################################
    API_V1_PREFIX: str = "/api/v1"

    ###############################################################
    # CORS Settings
    ###############################################################
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    ###############################################################
    # Auth Settings
    ###############################################################
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"  # noqa: S105
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ###############################################################
    # Initial Admin Settings
    ###############################################################
    ADMIN_EMAIL: str = "admin@rengine.local"
    ADMIN_USERNAME: str = "rengine"
    ADMIN_PASSWORD: str = "rengine@123"  # noqa: S105

    ###############################################################
    # Convenience Properties
    ###############################################################
    @property
    def database_url(self) -> str:
        """Database URL for API (async)."""
        return self.database_url_async

    ###############################################################
    # Validators
    ###############################################################
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Ensure SECRET_KEY is not using default value in production."""
        if (
            not info.data.get("DEBUG", False)
            and v == "change-me-in-production-use-openssl-rand-hex-32"
        ):
            msg = (
                "SECRET_KEY must be set in production. "
                "Generate one with: openssl rand -hex 32"
            )
            raise ValueError(msg)
        return v

    @field_validator("ADMIN_PASSWORD")
    @classmethod
    def validate_admin_password(cls, v: str, info) -> str:
        """Ensure ADMIN_PASSWORD is not using default value in production."""
        if not info.data.get("DEBUG", False) and v == "rengine@123":
            msg = "ADMIN_PASSWORD must be changed from default value in production"
            raise ValueError(msg)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
