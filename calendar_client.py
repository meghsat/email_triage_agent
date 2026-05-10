from pydantic import BaseModel, Field
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from pathlib import Path
from typing import Optional


class CalendarEvent(BaseModel):
    id: str
    summary: str
    start: datetime
    end: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    link: str
    attendees: list[str] = Field(default_factory=list)
    is_all_day: bool = False
    account_email: str = ""
    account_label: str = ""

    @property
    def duration_str(self) -> str:
        if self.is_all_day:
            return "All day"
        return f"{self.start.strftime('%I:%M %p')} - {self.end.strftime('%I:%M %p')}"

    @property
    def time_until(self) -> str:
        now = datetime.now(ZoneInfo("UTC"))
        delta = self.start - now

        if delta.total_seconds() < 0:
            return "In progress" if self.end > now else "Ended"

        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"In {hours}h {minutes}m"
        return f"In {minutes}m"


class CalendarClient:
    def __init__(self, credentials_file: str, token_file: str, scopes: list[str],
                 account_email: str = "", account_label: str = ""):
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.scopes = scopes
        self.account_email = account_email
        self.account_label = account_label
        self._service = None
        try:
            import tzlocal
            self.timezone = str(tzlocal.get_localzone())
        except:
            self.timezone = "UTC"

    @property
    def service(self):
        if self._service is None:
            creds = self._get_credentials()
            self._service = build('calendar', 'v3', credentials=creds)
        return self._service

    def _get_credentials(self) -> Credentials:
        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_file), self.scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file), self.scopes
                )
                creds = flow.run_local_server(port=0)

            self.token_file.write_text(creds.to_json())

        return creds

    def get_today_events(self) -> list[CalendarEvent]:
        tz = ZoneInfo(self.timezone)
        now = datetime.now(tz)

        start_of_day = datetime.combine(now.date(), time.min, tzinfo=tz)
        end_of_day = datetime.combine(now.date(), time.max, tzinfo=tz)

        return self.get_events_in_range(start_of_day, end_of_day)

    def get_events_in_range(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = []
        for event in events_result.get('items', []):
            try:
                start_dt = self._parse_datetime(event['start'])
                end_dt = self._parse_datetime(event['end'])
                is_all_day = 'date' in event['start']  # vs 'dateTime'

                attendees = [
                    a.get('email', '') for a in event.get('attendees', [])
                ]

                events.append(CalendarEvent(
                    id=event['id'],
                    summary=event.get('summary', '(No title)'),
                    start=start_dt,
                    end=end_dt,
                    location=event.get('location'),
                    description=event.get('description'),
                    link=event.get('htmlLink', ''),
                    attendees=attendees,
                    is_all_day=is_all_day,
                    account_email=self.account_email,
                    account_label=self.account_label
                ))
            except Exception as e:
                print(f"Error parsing event {event.get('id')}: {e}")
                continue

        return events

    @staticmethod
    def _parse_datetime(time_dict: dict) -> datetime:
        if 'dateTime' in time_dict:
            return datetime.fromisoformat(time_dict['dateTime'].replace('Z', '+00:00'))
        else:
            date = datetime.fromisoformat(time_dict['date'])
            return datetime.combine(date.date(), time.min, tzinfo=ZoneInfo("UTC"))
