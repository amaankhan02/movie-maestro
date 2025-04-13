from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str

    # Model Settings
    MODEL_NAME: str = "gpt-4o-mini"  # TODO: change to whatever is the cheapest model for now
    MODEL_TEMPERATURE: float = 0.7  

    # RAG Settings - TODO: implement this later
    VECTOR_DB_PATH: Optional[str] = None
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # API Settings
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    
    # frontend URL to allow the backend to be accessed from the frontend
    # TODO: change to the frontend URL when deployed
    CORS_ORIGINS: list = ["http://localhost:3000"]   

    class Config:
        env_file = ".env"


settings = Settings()
