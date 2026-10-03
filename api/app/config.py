from pydantic import field_validator

from shared.config import SECRET_KEY_MIN_LENGTH, BaseAppSettings

DEFAULT_ADMIN_PASSWORD = "rengine@123"  # noqa: S105
API_V1_PREFIX = "/api/v1"
ALGORITHM = "HS256"


class Settings(BaseAppSettings):
    JWT_SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    GLOBAL_RATE_LIMIT_PER_MINUTE: int = 600

    API_RELOAD: bool = True
    API_WORKERS: int = 4

    ADMIN_EMAIL: str = "admin@rengine.local"
    ADMIN_USERNAME: str = "rengine"
    ADMIN_PASSWORD: str = DEFAULT_ADMIN_PASSWORD

    @property
    def database_url(self) -> str:
        return self.database_url_async

    @field_validator("SECRET_KEY")
    @classmethod
    def require_secret_key(cls, v: str) -> str:
        if not v:
            msg = "SECRET_KEY is not set. Generate one with: openssl rand -hex 32"
            raise ValueError(msg)
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str, info) -> str:
        if v and not info.data.get("DEBUG", False) and len(v) < SECRET_KEY_MIN_LENGTH:
            msg = (
                f"JWT_SECRET_KEY must be at least {SECRET_KEY_MIN_LENGTH} characters. "
                "Generate one with: openssl rand -hex 32"
            )
            raise ValueError(msg)
        return v

    @field_validator("ADMIN_PASSWORD")
    @classmethod
    def validate_admin_password(cls, v: str, info) -> str:
        if not info.data.get("DEBUG", False) and v == DEFAULT_ADMIN_PASSWORD:
            msg = "ADMIN_PASSWORD must be changed from default value in production"
            raise ValueError(msg)
        return v


settings = Settings()
