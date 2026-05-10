from pydantic_settings import BaseSettings
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json


class AccountConfig(BaseModel):
    label: str  
    email: str  
    credentials_file: str  
    enabled: bool = True
    gmail_account_index: Optional[int] = None 

    def get_gmail_token_path(self) -> str:
        return f"tokens/{self.label}_gmail.json"

    def get_calendar_token_path(self) -> str:
        return f"tokens/{self.label}_calendar.json"

    def get_gmail_account_index(self, default_index: int) -> int:
        return self.gmail_account_index if self.gmail_account_index is not None else default_index


class AccountsConfig(BaseModel):
    accounts: list[AccountConfig]

    @classmethod
    def from_file(cls, file_path: str = "accounts.json") -> "AccountsConfig":
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Accounts config not found: {file_path}")

        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)

    def get_enabled_accounts(self) -> list[AccountConfig]:
        return [acc for acc in self.accounts if acc.enabled]


class Settings(BaseSettings):
    gmail_scopes: list[str] = ['https://www.googleapis.com/auth/gmail.readonly']
    calendar_scopes: list[str] = ['https://www.googleapis.com/auth/calendar.readonly']

    email_lookback_hours: int = 24
    refresh_interval_minutes: int = 20

    lemonade_server_url: str = "http://localhost:13305/v1"
    lemonade_model: str = "llama3.1:8b"
    lemonade_api_key: str = "not-needed"
    llm_chunk_size: int = 10

    # Account configuration file (mandatory)
    accounts_config_file: str = "accounts.json"

    class Config:
        env_file = ".env"
        env_prefix = ""


settings = Settings()
