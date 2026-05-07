"""Executor configuration loaded from environment variables."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutorConfig(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    sessions_dir: Path = Field(default=Path("/data/sessions"), validation_alias="SESSIONS_DIR")
    file_provider: str = Field(default="openai", validation_alias="FILE_PROVIDER")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", validation_alias="OPENAI_BASE_URL")


config = ExecutorConfig()
