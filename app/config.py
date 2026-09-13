from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./sysdesign.db"
    ai_provider: str = "mock"
    messaging_provider: str = "console"
    admin_token: str | None = None
    log_level: str = "INFO"
    timezone: str = "UTC"
    user_1_name: str = "Learner 1"
    user_1_phone: str = "+910000000001"
    user_2_name: str = "Learner 2"
    user_2_phone: str = "+910000000002"
    whatsapp_provider: str = "console"
    whatsapp_verify_token: str = ""
    daily_send_hour: int = 20
    summary_send_hour: int = 22

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
