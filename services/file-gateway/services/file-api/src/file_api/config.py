from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    aws_access_key_id: str
    aws_secret_access_key: str
    aws_endpoint_url: str
    bucket_name: str
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: str
    cors_allow_credentials: bool
    cors_allow_methods: str
    cors_allow_headers: str


settings = Settings()
