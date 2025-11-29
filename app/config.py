from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict

class Settings(BaseSettings):
    DEBUG: bool
    HOST: str
    PORT: int
    OPENLIGADB_BASE_URL: str
    OPENLIGADB_TIMEOUT: int
    RATE_LIMIT: Dict[str, int] = Field(default_factory=dict)
    RATE_WINDOW: Dict[str, int] = Field(default_factory=dict)
    BACKOFF_BASE_DELAY: float
    BACKOFF_MAX_DELAY: float
    BACKOFF_MAX_RETRIES: int
    BACKOFF_JITTER: bool
    LOG_LEVEL: str
    LOG_FORMAT: str
    LOG_BODY_LIMIT: int

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        env_nested_delimiter = "__"

settings = Settings()