"""
DigitalQ Labs — Orchestrator Configuration
Centralized settings for Celery workers, Kubernetes client, and infrastructure parameters.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Orchestrator environment configuration with sensible development defaults."""

    # --- Celery / Redis ---
    REDIS_URL: str = "redis://redis:6379/0"

    # --- Database (synchronous psycopg2 format) ---
    DATABASE_URL: str = "postgresql://postgres:supersecretpassword123@postgres:5432/digitalq_dev"

    # --- Kubernetes ---
    KUBECONFIG_PATH: str = ""  # Empty = auto-detect (in-cluster → ~/.kube/config)

    # --- Ingress ---
    INGRESS_DOMAIN_SUFFIX: str = "digitalqlabs.io"

    # --- Container Images ---
    CODE_SERVER_IMAGE: str = "digitalqlabs/code-server:v1.0.0"
    TERMINAL_AGENT_IMAGE: str = "digitalqlabs/terminal-agent:v1.0.0"

    # --- Lifecycle ---
    IDLE_TIMEOUT_MINUTES: int = 30
    PROVISION_TIMEOUT_SECONDS: int = 120
    PROVISION_POLL_INTERVAL: int = 3

    # --- Storage ---
    STORAGE_CLASS: str = "longhorn"

    # --- General ---
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
