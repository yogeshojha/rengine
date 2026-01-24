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
    # CORS Settings
    ###############################################################
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
