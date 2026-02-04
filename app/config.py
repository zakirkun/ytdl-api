from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # App settings
    APP_NAME: str = "YouTube Downloader API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Redis settings
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Download settings
    DOWNLOAD_DIR: str = "/tmp/downloads"
    MAX_FILE_SIZE_MB: int = 500
    
    # Cleanup settings
    FILE_RETENTION_HOURS: int = 2
    CLEANUP_INTERVAL_MINUTES: int = 30
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_PER_HOUR: int = 50
    
    # Celery settings
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    CELERY_WORKER_CONCURRENCY: int = 4
    
    # Video quality options
    AVAILABLE_QUALITIES: list = ["360", "480", "720", "1080"]
    DEFAULT_QUALITY: str = "720"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
