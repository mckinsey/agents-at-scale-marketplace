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
    # Uploads buffer in pod memory before reaching the provider; keep the cap
    # well under the container memory limit (512Mi in the default chart).
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")

    # Defaults used by the /chat endpoint when no ?agent= is specified or the
    # agent can't be resolved from k8s (e.g. local dev without a cluster). When
    # ?agent= resolves successfully, the agent's Model + prompt override these.
    default_chat_model: str = Field(default="gpt-4o-mini", validation_alias="DEFAULT_CHAT_MODEL")
    default_chat_instructions: str = Field(
        default="You are a helpful assistant. When the user attaches files, read them and answer based on their contents.",
        validation_alias="DEFAULT_CHAT_INSTRUCTIONS",
    )


config = ExecutorConfig()
