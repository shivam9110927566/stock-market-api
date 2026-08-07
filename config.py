from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Stock Market API"
    DATABASE_URL: str = "sqlite+aiosqlite:///./stock_api.db"
    
    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()
