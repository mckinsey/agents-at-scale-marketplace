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

    # Files API (used by /v1/files endpoints and the /files upload UI). When a
    # request specifies ?agent=<name>, credentials come from the agent's Model
    # CR instead and these values act as a cluster-wide fallback.
    file_provider: str = Field(default="openai", validation_alias="FILE_PROVIDER")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", validation_alias="OPENAI_BASE_URL")


config = ExecutorConfig()
