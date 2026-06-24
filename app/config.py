from pydantic_settings import BaseSettings

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "acteu_dev"
    REDIS_URL: str = DEFAULT_REDIS_URL
    CELERY_BROKER_URL: str = DEFAULT_REDIS_URL
    CELERY_RESULT_BACKEND: str = DEFAULT_REDIS_URL
    JWT_SECRET: str = "changeme"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    DOCUMENT_SEARCH_LIMIT: int = 5000
    CLASSIFIER_DIR: str = "/app/classifiers"
    EMBEDDING_CACHE_DIR: str = "/app/embedding_cache"
    OLLAMA_URL: str = "university-api" # Stored in .env
    OLLAMA_MODEL: str = "gemma4:26b"
    HF_TOKEN: str = "changeme"
    LLM_API_KEY: str = "changeme"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
