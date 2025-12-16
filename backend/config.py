from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str
    SERPER_API_KEY: str
    OPENAI_ORG_ID: str = ""

    # App settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # File storage
    UPLOAD_DIR: Path = Path("./data/uploads")
    RESULTS_DIR: Path = Path("./data/results")
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB

    # Processing settings
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_URL: str = "https://api.openai.com/v1/chat/completions"
    SERPER_SEARCH_URL: str = "https://google.serper.dev/search"

    SERP_MAX_RPS: int = 50
    SERP_CONCURRENCY: int = 100
    OPENAI_CONCURRENCY: int = 24
    HTTP_CONNECT_TIMEOUT: int = 8
    HTTP_READ_TIMEOUT: int = 45
    MAX_RETRIES: int = 4
    BACKOFF_BASE: float = 1.6

    MAX_CANDIDATES_PER_COMPANY: int = 8
    SEARCH_RESULTS_PER_CALL: int = 12
    CHECKPOINT_EVERY: int = 20
    ENABLE_DNS_CHECK: bool = False
    DNS_TIMEOUT_SEC: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
