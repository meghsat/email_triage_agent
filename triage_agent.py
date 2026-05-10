from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import settings, AccountsConfig
from gmail_client import GmailClient, Email
from calendar_client import CalendarClient, CalendarEvent
from lemonade_client import LemonadeClient, EmailAnalysis


class TriageResult(BaseModel):
    emails: list[Email]
    analysis: Optional[EmailAnalysis]
    emails_needing_response: list[Email]
    calendar_events: list[CalendarEvent]
    last_updated: datetime
    errors: list[str] = []

    class Config:
        arbitrary_types_allowed = True


class TriageAgent:
    def __init__(self):
        # Load accounts configuration (mandatory)
        self.accounts_config = AccountsConfig.from_file(settings.accounts_config_file)
        self.enabled_accounts = self.accounts_config.get_enabled_accounts()

        # Ensure tokens directory exists
        Path("tokens").mkdir(exist_ok=True)

        # Create client pairs for each account
        self.gmail_clients = []
        self.calendar_clients = []

        for idx, account in enumerate(self.enabled_accounts):
            gmail_client = GmailClient(
                credentials_file=account.credentials_file,
                token_file=account.get_gmail_token_path(),
                scopes=settings.gmail_scopes,
                account_email=account.email,
                account_label=account.label,
                account_index=account.get_gmail_account_index(idx)
            )

            calendar_client = CalendarClient(
                credentials_file=account.credentials_file,
                token_file=account.get_calendar_token_path(),
                scopes=settings.calendar_scopes,
                account_email=account.email,
                account_label=account.label
            )

            self.gmail_clients.append(gmail_client)
            self.calendar_clients.append(calendar_client)

        self.llm = LemonadeClient()

    async def run_triage(self) -> TriageResult:
        errors = []
        all_emails = []
        all_events = []

        num_accounts = len(self.enabled_accounts)
        max_workers = min(num_accounts * 2, 10)  # Cap at 10 parallel tasks

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            # Submit all fetch tasks
            for idx, account in enumerate(self.enabled_accounts):
                email_future = executor.submit(
                    self._fetch_emails_for_account,
                    self.gmail_clients[idx],
                    account.email
                )
                calendar_future = executor.submit(
                    self._fetch_calendar_for_account,
                    self.calendar_clients[idx],
                    account.email
                )
                futures.append(('email', account.email, email_future))
                futures.append(('calendar', account.email, calendar_future))

            # Collect results
            for fetch_type, account_email, future in futures:
                result = await asyncio.wrap_future(future)
                data, error = result

                if error:
                    errors.append(f"{account_email} {fetch_type}: {error}")
                elif data:
                    if fetch_type == 'email':
                        all_emails.extend(data)
                    else:
                        all_events.extend(data)

        # LLM analysis on combined emails from all accounts
        analysis = None
        emails_needing_response = []

        if all_emails:
            try:
                analysis = self.llm.analyze_emails(all_emails)

                response_ids = set(analysis.needs_response_ids)
                emails_needing_response = [
                    email for email in all_emails
                    if email.message_id in response_ids
                ]
            except Exception as e:
                errors.append(f"LLM: {str(e)}")

        return TriageResult(
            emails=all_emails,
            analysis=analysis,
            emails_needing_response=emails_needing_response,
            calendar_events=all_events,
            last_updated=datetime.now(),
            errors=errors
        )

    def _fetch_emails_for_account(
        self,
        client: GmailClient,
        account_email: str
    ) -> tuple[Optional[list[Email]], Optional[str]]:
        """Fetch emails for a specific account"""
        try:
            emails = client.get_recent_emails(hours=settings.email_lookback_hours)
            return emails, None
        except Exception as e:
            return None, str(e)

    def _fetch_calendar_for_account(
        self,
        client: CalendarClient,
        account_email: str
    ) -> tuple[Optional[list[CalendarEvent]], Optional[str]]:
        """Fetch calendar events for a specific account"""
        try:
            events = client.get_today_events()
            return events, None
        except Exception as e:
            return None, str(e)


_agent = None


def get_agent() -> TriageAgent:
    global _agent
    if _agent is None:
        _agent = TriageAgent()
    return _agent
