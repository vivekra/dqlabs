import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:supersecretpassword123@postgres:5432/digitalq_dev"
    REDIS_URL: str = "redis://redis:6379/0"
    SUPABASE_JWT_SECRET: str = "supersecretjwtsecretstring1234567890"
    PAYMENTER_API_KEY: str = "dev_paymenter_api_key_abc123"
    PAYMENTER_URL: str = "http://paymenter:80"
    
    # Ingress Domain Strategy: workspace-id.tenant-id.digitalqlabs.io
    INGRESS_DOMAIN_SUFFIX: str = "digitalqlabs.io"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
