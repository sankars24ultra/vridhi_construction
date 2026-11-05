from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vridhi Constructions & Designs"
    database_url: str = "postgresql+asyncpg://vridhi_app:vridhi_local_only@localhost:5433/vridhi_dev"
    session_secret: str = "local-only-change-this-secret-before-sharing"
    session_days: int = 7
    upload_directory: Path = Path(__file__).resolve().parents[4] / "data" / "uploads"
    upload_max_bytes: int = 10 * 1024 * 1024
    log_directory: Path = Path(__file__).resolve().parents[4] / "data" / "logs"
    initial_password_hash: str = "$argon2id$v=19$m=65536,t=3,p=4$uWjpJSNnahWV6ZlrEvSITA$fK9S5DhjaUM7NADnLqCdqBJKyUGWN+ybGH+A+MdwBj4"
    cookie_secure: bool = False

    @field_validator("upload_directory")
    @classmethod
    def resolve_upload_directory(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return Path(__file__).resolve().parents[4] / value

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[4] / ".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()