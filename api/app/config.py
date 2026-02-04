from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ################################################################
    # Application Settings
    ###############################################################
    APP_NAME: str = "reNgine"
    DEBUG: bool = False
    APP_VERSION: str = "dev"  # Overwritten by VERSION file
    API_V1_PREFIX: str = "/api/v1"

    ###############################################################
    # Logging Settings
    ###############################################################
    LOG_LEVEL: str = "INFO"

    ###############################################################
    # CORS Settings
    ###############################################################
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    ###############################################################
    # Database Settings
    ###############################################################
    DATABASE_URL: str = "postgresql+asyncpg://rengine:rengine@db:5432/rengine"

    ###############################################################
    # Auth configs
    ###############################################################
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"  # noqa: S105
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ###############################################################
    # Initial Admin COnfigs
    ###############################################################
    ADMIN_EMAIL: str = "admin@rengine.local"
    ADMIN_USERNAME: str = "rengine"
    ADMIN_PASSWORD: str = "rengine@123"  # noqa: S105

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Ensure SECRET_KEY is not using default value in production."""
        if (
            not info.data.get("DEBUG", False)
            and v == "change-me-in-production-use-openssl-rand-hex-32"
        ):
            return_error = (
                "SECRET_KEY must be set in production. "
                "Generate one with: openssl rand -hex 32"
            )
            raise ValueError(return_error)
        return v

    @field_validator("ADMIN_PASSWORD")
    @classmethod
    def validate_admin_password(cls, v: str, info) -> str:
        """Ensure ADMIN_PASSWORD is not using default value in production."""
        if not info.data.get("DEBUG", False) and v == "rengine@123":
            return_error = (
                "ADMIN_PASSWORD must be changed from default value in production"
            )
            raise ValueError(return_error)
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
