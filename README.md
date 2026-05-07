# Personal Triage Agent

An intelligent email and calendar triage system that uses a local LLM (via Lemonade server) to analyze your emails and calendar events, providing a clean dashboard with actionable insights.

## Features

- **Email Analysis**: Fetch and analyze emails from the last 24 hours
- **Local LLM Processing**: Uses your Lemonade server for privacy and offline analysis
- **Smart Categorization**: Automatically categorizes emails (work, personal, newsletters, promotions, etc.)
- **Action Items**: Highlights emails requiring your response
- **Calendar Integration**: Shows today's events with time-until countdown
- **Auto-refresh**: Automatically updates every 20 minutes

## Prerequisites

- **Python 3.9+**
- **Lemonade server** running on port 13305
- **Google Cloud Project** with Gmail & Calendar APIs enabled

## Setup Instructions

### 1. Install Dependencies

```bash
cd C:\Users\sdevinen\Downloads\projects\agents\triage\personal_triage_agent
pip install -r requirements.txt
```

### 2. Configure Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable APIs:
   - Gmail API
   - Google Calendar API
4. Create OAuth 2.0 credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Download the credentials as `credentials.json`
5. Place `credentials.json` in the project directory


More:
Complete OAuth 2.0 Setup Guide
Step 1: Create/Access Google Cloud Project
1. Visit: https://console.cloud.google.com/
2. Click the project dropdown at the top and "New Project"
Step 2: Enable Required APIs
Navigate to APIs & Services:
1. In the left sidebar, click "APIs & Services" → "Enabled APIs & services"
2. Search for Gmail and Calendar APIs and enable them.
Step 3: Configure OAuth Consent Screen
1. Left sidebar: "APIs & Services" → "OAuth consent screen"
2. Give a name, enter your account's email, choose "External", save, and create
3. Left sidebar: "Data access" -> Add or remove scopes. In the filter bar, search for these 2 and save
   .../auth/gmail.readonly (Read-only Gmail access)
   .../auth/calendar.readonly (Read-only Calendar access)
Step 4: Create OAuth 2.0 Credentials
1. Left sidebar: "APIs & Services" → "Credentials"
2. Click "+ CREATE CREDENTIALS" at the top, Select "OAuth client ID"
3. Configure the OAuth client:
   Application type: Select "Desktop app"
   Name: "Personal Triage Desktop Client" (or any name you prefer)
   Click "CREATE"
4. Download JSON in the pop-up
Step 5: Setup Credentials File
1. The file will be named something like client_secret_XXXXX.json
2. Rename it to: credentials.json and move it to your project directory:


# Move the file to your project folder
mv ~/Downloads/credentials.json "C:\Users\sdevinen\Downloads\projects\agents\triage\personal_triage_agent\credentials.json"
Or manually copy/paste it into:
C:\Users\sdevinen\Downloads\projects\agents\triage\personal_triage_agent\

### 3. Configure Environment

The `.env` file is already created with defaults:

```env
LEMONADE_SERVER_URL=http://localhost:13305/v1
LEMONADE_MODEL=user.Llama-3.2-3B-Instruct-GGUF
```

Modify if your Lemonade server is on a different port or you want to use a different model.

### 4. Verify Lemonade Server

Check that your Lemonade server is running:

```bash
lemonade status
```

You should see output showing the server is running on port 13305.

### 5. First Run - OAuth Authentication

The first time you run the dashboard, it will open a browser window for OAuth authentication:

```bash
streamlit run dashboard.py
```

1. Browser opens automatically for Gmail OAuth → Sign in and authorize
2. Browser opens again for Calendar OAuth → Sign in and authorize
3. Tokens are saved to `gmail_token.json` and `calendar_token.json`
4. Future runs will use these tokens (auto-refreshed when needed)

## Running the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser at: `http://localhost:8501`

## Dashboard Sections

### Email Summary
- Total emails, unread count, urgent count
- LLM-generated summary of main topics
- Categorized emails (expandable sections)
- View all emails option

### Emails Needing Response
- Emails identified by LLM as requiring action
- Direct links to open in Gmail
- Sender and timestamp info

### Today's Calendar
- All events for today
- Time-until countdown for upcoming events
- Location and attendee information
- Direct links to Google Calendar

## Configuration

Edit `config.py` or `.env` to customize:

- `email_lookback_hours`: How many hours of email history to fetch (default: 24)
- `refresh_interval_minutes`: Auto-refresh interval (default: 20)
- `lemonade_server_url`: Your Lemonade server endpoint
- `lemonade_model`: Model name to use for analysis