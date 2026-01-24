from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    ################################################################
    # Application Settings
    ###############################################################
    APP_NAME: str = "reNgine"
    DEBUG: bool = False
    APP_VERSION: str = "dev" # Overwritten by VERSION file
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
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ###############################################################
    # Initial Admin COnfigs
    ###############################################################
    ADMIN_EMAIL: str = "admin@rengine.local"
    ADMIN_USERNAME: str = "rengine"
    ADMIN_PASSWORD: str = "rengine@123"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
