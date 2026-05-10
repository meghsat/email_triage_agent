# Personal Triage Agent

An intelligent email and calendar triage system that uses a local LLM via Lemonade Server to analyze your emails and calendar events, then presents actionable insights in a clean Streamlit dashboard.

## Features

- Analyze emails from the last 24 hours
- Local LLM processing for privacy and offline usage
- Automatic email categorization:
  - Work
  - Personal
  - Newsletters
  - Promotions
  - Alerts
- Detect emails that require a response
- Display today's calendar events with countdowns
- Auto-refresh dashboard every 20 minutes
- Direct links to Gmail and Google Calendar

---

# Requirements

- Python 3.9+
- Google Cloud Project with:
  - Gmail API enabled
  - Google Calendar API enabled
- Lemonade Server running locally

---

# Installing Lemonade Server

This project uses Lemonade Server as the local LLM backend.

Installation instructions:

https://lemonade-server.ai/

After installation, verify the server is running:

```bash
lemonade status
```

By default, this project expects Lemonade Server at:

```text
http://localhost:13305/v1
```

---

# Project Setup

## 1. Clone the Repository

```bash
git clone <your-repo-url>
cd personal_triage_agent
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure Google Cloud

## Step 1: Create or Select a Google Cloud Project

1. Open:
   https://console.cloud.google.com/
2. Create a new project or select an existing one

---

## Step 2: Enable Required APIs

Navigate to:

```text
APIs & Services → Enabled APIs & services
```

Enable:

- Gmail API
- Google Calendar API

---

## Step 3: Configure OAuth Consent Screen

Navigate to:

```text
APIs & Services → OAuth consent screen
```

Configuration:

- User Type: External
- App Name: Any name you prefer
- Support Email: Your Google account email

Save and continue.

---

## Step 4: Add Test User

Navigate to:

```text
APIs & Services → OAuth consent screen → Audience
```

Add your email under the test users, save, and continue.

---

## Step 5: Add Required OAuth Scopes

Navigate to:

```text
APIs & Services → OAuth consent screen → Data Access
```

Add these scopes:

```text
.../auth/gmail.readonly
.../auth/calendar.readonly
```

These provide read-only access to Gmail and Calendar.

---

## Step 6: Create OAuth Credentials

Navigate to:

```text
APIs & Services → Credentials
```

Create credentials:

1. Click:
   ```text
   + CREATE CREDENTIALS
   ```
2. Select:
   ```text
   OAuth client ID
   ```
3. Application type:
   ```text
   Desktop app
   ```
4. Name:
   ```text
   Personal Triage Desktop Client
   ```

Download the generated JSON file.

---

## 4. Add Credentials File

Rename the downloaded file to:

```text
credentials_{i}.json
```

Place it in the project root directory:

```text
personal_triage_agent/
│
├── credentials_{i}.json
├── dashboard.py
├── requirements.txt
└── ...
```

## 5. Add account details - accounts.json

Create this file in your project root depending on the number of emails you want to track:

```json
{
  "accounts": [
    {
      "label": "personal_1",
      "email": "@gmail.com",
      "credentials_file": "credentials_1.json",
      "enabled": true
    },
    {
      "label": "personal_2",
      "email": "@gmail.com",
      "credentials_file": "credentials_2.json",
      "enabled": true
    }
  ]
}

---

# Environment Configuration

Create a `.env` file in the project root:

```env
LEMONADE_SERVER_URL=http://localhost:13305/v1
LEMONADE_MODEL=user.Llama-3.2-3B-Instruct-GGUF
```

Modify these values if:

- Your Lemonade Server runs on another port
- You want to use a different model

---

# Running the Dashboard

Start the Streamlit app:

```bash
streamlit run dashboard.py
```

The dashboard will open at:

```text
http://localhost:8501
```

---

# First Run Authentication

On first launch:

1. A browser window opens for Gmail OAuth
2. Sign in and approve access
3. A second browser window opens for Calendar OAuth
4. Sign in and approve access

Generated token files:

```text
gmail_token.json
calendar_token.json
```

These tokens are reused automatically and refreshed when needed.

---

# Dashboard Overview

## Email Summary

Displays:

- Total email count
- Unread emails
- Urgent emails
- AI-generated summaries
- Categorized email sections

---

## Emails Requiring Response

Highlights emails likely needing action:

- Sender information
- Timestamp
- Direct Gmail links

---

## Today's Calendar

Displays:

- Upcoming events
- Countdown until each event
- Location information
- Attendees
- Direct Google Calendar links

---

# Configuration Options

You can customize settings in `config.py` or `.env`.

Available settings:

| Setting | Description | Default |
|---|---|---|
| `email_lookback_hours` | Hours of email history to analyze | `24` |
| `refresh_interval_minutes` | Dashboard refresh interval | `20` |
| `lemonade_server_url` | Lemonade API endpoint | `http://localhost:13305/v1` |
| `lemonade_model` | Model used for analysis | `user.Llama-3.2-3B-Instruct-GGUF` |

---

# Tech Stack

- Python
- Streamlit
- Gmail API
- Google Calendar API
- Lemonade Server
- Local LLM inference

---

# Security and Privacy

- Email and calendar analysis runs locally through Lemonade Server
- No external LLM APIs required
- OAuth tokens remain on your machine
- Read-only Gmail and Calendar access