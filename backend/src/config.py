import os
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str
    TMDB_API_KEY: str

    # Model Settings
    MODEL_NAME: str = "gpt-4"  # TODO: change to whatever is the cheapest model for now
    MODEL_TEMPERATURE: float = 0.3

    # Data Source Settings
    ENABLE_TMDB: bool = True
    ENABLE_WIKIPEDIA: bool = True

    # RAG Settings - TODO: implement this later
    VECTOR_DB_PATH: Optional[str] = None
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # API Settings
    API_HOST: str = "localhost"
    API_PORT: int = 8000

    # frontend URL to allow the backend to be accessed from the frontend
    CORS_ORIGINS: str = "http://localhost:3000"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
