from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-6-sol"
    openai_reasoning_effort: str = "low"
    agent_max_revisions: int = Field(default=1, ge=0, le=2)
    agent_quality_threshold: float = Field(default=0.8, ge=0, le=1)
    registry_batch_size: int = Field(default=35, ge=1, le=60)
    registry_workers: int = Field(default=3, ge=1, le=4)
    registry_match_batch_size: int = Field(default=20, ge=1, le=35)
    registry_max_batches: int = Field(default=40, ge=1, le=60)
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
