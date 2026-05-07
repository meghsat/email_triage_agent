from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    gmail_scopes: list[str] = ['https://www.googleapis.com/auth/gmail.readonly']
    calendar_scopes: list[str] = ['https://www.googleapis.com/auth/calendar.readonly']

    email_lookback_hours: int = 24
    refresh_interval_minutes: int = 20

    lemonade_server_url: str = "http://localhost:13305/v1"
    lemonade_model: str = "llama3.1:8b"
    lemonade_api_key: str = "not-needed"

    credentials_file: str = "credentials.json"
    gmail_token_file: str = "gmail_token.json"
    calendar_token_file: str = "calendar_token.json"

    class Config:
        env_file = ".env"
        env_prefix = ""


settings = Settings()
