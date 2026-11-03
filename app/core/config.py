from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Open Timetable Generator"
    app_version: str = "0.1.0"
    debug: bool = True
    database_url: str = "sqlite:///./data/open_timetable.db"
    timetable_config_path: str = "config/timetable.toml"
    output_dir: str = "output"
    log_level: str = "INFO"

    # Authentication. Without SECRET_KEY a random key is generated once and
    # stored in ``secret_key_file``.
    secret_key: str | None = None
    secret_key_file: str = "data/.secret_key"
    session_hours: int = 12
    cookie_secure: bool = False  # set TRUE when served over HTTPS

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
