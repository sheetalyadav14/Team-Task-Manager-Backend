from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Team Task Manager")
    app_env: Literal["development", "production", "test"] = Field(default="development")
    port: int = Field(default=8000)

    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_db_name: str = Field(default="team_task_manager")

    jwt_secret: str = Field(default="dev-only-insecure-secret-change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expires_minutes: int = Field(default=60 * 24 * 7)

    client_origin: str = Field(default="http://localhost:5173")


@lru_cache
def get_settings() -> Settings:
    return Settings()
