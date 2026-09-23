from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    openai_api_key: str = ""
    openai_model: str = "gpt-6-sol"
    openai_reasoning_effort: str = "low"
    cors_origins: str = "http://localhost:3001,http://localhost:9000"
    upload_dir: str = "/tmp/ai-first/uploads"
    max_file_size_mb: int = 20

    model_config = SettingsConfigDict(env_file=".back_env", extra="ignore")

    @field_validator("openai_model", mode="before")
    @classmethod
    def default_model_when_empty(cls, value: str | None) -> str:
        return value or "gpt-6-sol"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
