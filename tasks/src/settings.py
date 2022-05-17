from pydantic import BaseSettings


class Settings(BaseSettings):

    BIND_PORT: int = 8000
    ELASTICSEARCH_URL: str = "http://elasticsearch"
    ELASTICSEARCH_PORT: int = 9200

    REDIS_HOST: str = "0.0.0.0"
    REDIS_PORT: int = 6379

    UVICORN_RELOAD: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
