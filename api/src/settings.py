from pydantic import BaseSettings

class Settings(BaseSettings):

    BIND_PORT: int = 8000
    ELASTICSEARCH_URL: str
    ELASTICSEARCH_PORT: int = 9200
    DMC_URL: str
    DMC_PORT: int = 8080
    DMC_USER: str
    DMC_PASSWORD: str
    DMC_LOCAL_DIR: str

    DOJO_URL: str

    UVICORN_RELOAD: bool = False

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

