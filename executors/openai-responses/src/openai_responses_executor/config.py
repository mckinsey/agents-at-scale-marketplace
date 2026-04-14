"""Executor configuration loaded from environment variables."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutorConfig(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    sessions_dir: Path = Field(default=Path("/data/sessions"), validation_alias="SESSIONS_DIR")
    max_tool_iterations: int = Field(default=10, validation_alias="MAX_TOOL_ITERATIONS")


config = ExecutorConfig()
