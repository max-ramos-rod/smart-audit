from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "Smart Audit API"
    app_env: str = "development"
    app_debug: bool = True
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    allowed_origins: list[str] = ["http://localhost:5174", "http://127.0.0.1:5174"]
    upload_dir: str = "uploads"
    upload_base_url: str = "http://localhost:8003/uploads"
    # URL base onde o SPA esta publicado, incluindo o base path (ex.: /app).
    # Usada para montar links absolutos enviados por e-mail (reset de senha).
    # Em producao: https://smartaudit.goevolux.com.br/app
    frontend_url: str = "http://localhost:5174/app"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "noreply@smartaudit.local"
    # TTL do link de convite de usuario (mais longo que o reset de senha,
    # pois o convidado pode demorar a abrir o e-mail)
    invite_token_ttl_hours: int = 72

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()