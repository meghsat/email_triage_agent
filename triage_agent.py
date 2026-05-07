from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config import settings
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
        self.gmail = GmailClient(
            credentials_file=settings.credentials_file,
            token_file=settings.gmail_token_file,
            scopes=settings.gmail_scopes
        )
        self.calendar = CalendarClient(
            credentials_file=settings.credentials_file,
            token_file=settings.calendar_token_file,
            scopes=settings.calendar_scopes
        )
        self.llm = LemonadeClient()

    async def run_triage(self) -> TriageResult:
        errors = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            email_future = executor.submit(self._fetch_emails)
            calendar_future = executor.submit(self._fetch_calendar)

            emails = await asyncio.wrap_future(email_future)
            events = await asyncio.wrap_future(calendar_future)

        emails_data, email_error = emails
        events_data, calendar_error = events

        if email_error:
            errors.append(f"Gmail: {email_error}")
        if calendar_error:
            errors.append(f"Calendar: {calendar_error}")

        analysis = None
        emails_needing_response = []

        if emails_data:
            try:
                analysis = self.llm.analyze_emails(emails_data)

                response_ids = set(analysis.needs_response_ids)
                emails_needing_response = [
                    email for email in emails_data
                    if email.message_id in response_ids
                ]
            except Exception as e:
                errors.append(f"LLM: {str(e)}")

        return TriageResult(
            emails=emails_data or [],
            analysis=analysis,
            emails_needing_response=emails_needing_response,
            calendar_events=events_data or [],
            last_updated=datetime.now(),
            errors=errors
        )

    def _fetch_emails(self) -> tuple[Optional[list[Email]], Optional[str]]:
        try:
            emails = self.gmail.get_recent_emails(hours=settings.email_lookback_hours)
            return emails, None
        except Exception as e:
            return None, str(e)

    def _fetch_calendar(self) -> tuple[Optional[list[CalendarEvent]], Optional[str]]:
        try:
            events = self.calendar.get_today_events()
            return events, None
        except Exception as e:
            return None, str(e)


_agent = None


def get_agent() -> TriageAgent:
    global _agent
    if _agent is None:
        _agent = TriageAgent()
    return _agent
