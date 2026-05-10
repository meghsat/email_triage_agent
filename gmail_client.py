from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import re
from pathlib import Path
from typing import Optional


class Email(BaseModel):
    message_id: str
    thread_id: str
    subject: str
    sender: str
    date: datetime
    snippet: str
    link: str
    labels: list[str] = Field(default_factory=list)
    is_unread: bool = False
    account_email: str = ""  # Source account identifier
    account_label: str = ""  # Display label (e.g., "Work", "Personal")
    account_index: int = 0   # Gmail u/X account index

    @property
    def date_str(self) -> str:
        return self.date.strftime("%Y-%m-%d %I:%M %p")


class GmailClient:
    def __init__(self, credentials_file: str, token_file: str, scopes: list[str],
                 account_email: str = "", account_label: str = "", account_index: int = 0):
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.scopes = scopes
        self.account_email = account_email
        self.account_label = account_label
        self.account_index = account_index
        self._service = None

    @property
    def service(self):
        if self._service is None:
            creds = self._get_credentials()
            self._service = build('gmail', 'v1', credentials=creds)
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

    def get_recent_emails(self, hours: int = 24, max_results: int = 100) -> list[Email]:
        after_timestamp = int((datetime.now() - timedelta(hours=hours)).timestamp())
        query = f'after:{after_timestamp}'

        results = self.service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg_ref in messages:
            try:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=msg_ref['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()

                headers = {h['name']: h['value'] for h in msg['payload']['headers']}

                emails.append(Email(
                    message_id=msg['id'],
                    thread_id=msg['threadId'],
                    subject=headers.get('Subject', '(No subject)'),
                    sender=self._parse_sender(headers.get('From', '')),
                    date=self._parse_date(headers.get('Date', '')),
                    snippet=msg.get('snippet', ''),
                    link=f"https://mail.google.com/mail/u/{self.account_index}/#inbox/{msg['id']}",
                    labels=msg.get('labelIds', []),
                    is_unread='UNREAD' in msg.get('labelIds', []),
                    account_email=self.account_email,
                    account_label=self.account_label,
                    account_index=self.account_index
                ))
            except Exception as e:
                print(f"Error fetching email {msg_ref['id']}: {e}")
                continue

        return emails

    @staticmethod
    def _parse_sender(from_header: str) -> str:
        match = re.match(r'^"?([^"<]+)"?\s*<?([^>]+)?>?', from_header)
        if match:
            name, email = match.groups()
            return name.strip() if name.strip() else email.strip()
        return from_header.strip()

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_str)
        except:
            return datetime.now()
