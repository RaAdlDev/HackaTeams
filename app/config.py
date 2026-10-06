from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str
    database_url: str

    # JWT
    secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    bcrypt_rounds: int = 12 

    auto_create_tables: bool = False

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
