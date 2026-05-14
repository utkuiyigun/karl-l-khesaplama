"""
Ortam değişkenlerinden konfigürasyon.

NOT: FERNET_KEY ZORUNLU. Üretmek için:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # App
    debug: bool = False
    log_level: str = "INFO"

    # DB
    database_url: str = Field(..., description="postgresql+asyncpg://...")

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Şifreleme — Müşteri API key'lerini şifrelemek için
    fernet_key: str = Field(..., description="32-byte url-safe base64 Fernet key")

    # Trendyol
    trendyol_base_url: str = "https://api.trendyol.com/sapigw"
    trendyol_user_agent_suffix: str = "MelonKar"

    # Sync
    sync_interval_minutes: int = 5


settings = Settings()
