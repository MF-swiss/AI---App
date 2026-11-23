from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    assistant_name: str = "Lokaler Code-Assistent"
    openai_api_key: str = ""
    openai_model: str = "lokal"
    project_root: Path = Path(".")
    execution_timeout_seconds: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
