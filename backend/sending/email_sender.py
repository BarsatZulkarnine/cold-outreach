import asyncio
import base64
import random
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import (
    GMAIL_CREDENTIALS_PATH,
    GMAIL_TOKEN_PATH,
    MAX_EMAILS_PER_DAY,
)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class DailyLimitReachedError(Exception):
    pass


def _get_gmail_service():
    """Authenticate and return a Gmail API service object."""
    import os
    import json

    creds = None

    if os.path.exists(GMAIL_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Gmail credentials file not found at {GMAIL_CREDENTIALS_PATH}. "
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(GMAIL_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _build_mime_message(to_email: str, subject: str, body: str) -> str:
    """Build a base64-encoded MIME message."""
    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["from"] = "mohammedbarsatzulkarnine@gmail.com"
    message["subject"] = subject

    # Plain text part
    text_part = MIMEText(body, "plain")
    message.attach(text_part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return raw


async def _check_daily_limit(db) -> int:
    """Check how many emails have been sent today. Raises if limit hit."""
    from sqlalchemy import select, func
    from models.schemas import Message

    today_start = datetime.combine(date.today(), datetime.min.time())
    result = await db.execute(
        select(func.count(Message.id)).where(
            Message.channel == "email",
            Message.sent_at >= today_start,
            Message.sent_at.isnot(None),
        )
    )
    count = result.scalar() or 0

    if count >= MAX_EMAILS_PER_DAY:
        raise DailyLimitReachedError(
            f"Daily email limit reached ({MAX_EMAILS_PER_DAY}). Try again tomorrow."
        )

    return count


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    message_id: int,
    db,
) -> bool:
    """
    Send an email via Gmail API.
    Updates the message record in DB on success.
    Applies random delay after sending.
    """
    from sqlalchemy import select
    from models.schemas import Message, Target

    # Check daily limit
    sent_today = await _check_daily_limit(db)
    print(f"[Email] Sending ({sent_today + 1}/{MAX_EMAILS_PER_DAY} today) → {to_email}")

    try:
        service = _get_gmail_service()
        raw = _build_mime_message(to_email, subject, body)
        service.users().messages().send(
            userId="me",
            body={"raw": raw},
        ).execute()
    except Exception as e:
        print(f"[Email] Send failed to {to_email}: {e}")
        return False

    # Update message record
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if msg:
        msg.sent_at = datetime.utcnow()
        msg.status = "sent"

        # Update target status
        target_result = await db.execute(select(Target).where(Target.id == msg.target_id))
        target = target_result.scalar_one_or_none()
        if target and target.status in ("discovered", "message_generated", "approved"):
            target.status = "sent"
            target.updated_at = datetime.utcnow()

        await db.commit()

    # Random delay to avoid rate-limiting / spam detection
    delay = random.uniform(30, 90)
    print(f"[Email] Sent ✓. Waiting {delay:.0f}s before next send.")
    await asyncio.sleep(delay)

    return True
