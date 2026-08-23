from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json

class Settings(BaseSettings):
    app_env: str = "development"
    app_url: str = "http://localhost:8000"
    allowed_origins: str | List[str] = ["*"]
    database_url: str = ""
    llm_provider: str = "groq"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    anthropic_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    email_provider: str = "smtp"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    lead_email_to: str = "info@moinsystemsai.com"
    app_secret: str = ""
    rate_limit: str = "100/minute"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_allowed_origins(self) -> List[str]:
        if isinstance(self.allowed_origins, str):
            try:
                return json.loads(self.allowed_origins)
            except ValueError:
                return [self.allowed_origins]
        return self.allowed_origins

settings = Settings()