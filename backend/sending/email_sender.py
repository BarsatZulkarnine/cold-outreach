import asyncio
import base64
import random
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from zoneinfo import ZoneInfo

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


def calculate_next_send_slot(offset_minutes: int = 0) -> datetime:
    """
    Returns the next optimal email send time in Melbourne timezone.
    Valid days: Tue, Wed, Thu (weekday indices 1, 2, 3).
    Valid windows (Melbourne local time):
      - 08:30
      - 10:30–12:00 (random)
      - 17:00–18:00 (random)
    Returns a UTC datetime.
    offset_minutes: stagger multiple scheduled messages (add N minutes between slots).
    """
    tz = ZoneInfo("Australia/Melbourne")
    now = datetime.now(tz) + timedelta(minutes=offset_minutes)

    # Define time windows as (hour, minute_min, minute_max)
    windows = [
        (8, 30, 30),    # exactly 08:30
        (10, 30, 60),   # 10:30–11:30
        (17, 0, 60),    # 17:00–18:00
    ]

    candidate = now
    for _ in range(14):  # search up to 2 weeks ahead
        candidate += timedelta(minutes=1) if candidate == now else timedelta(days=0)
        # Move to next valid weekday if needed (Tue=1, Wed=2, Thu=3)
        while candidate.weekday() not in (1, 2, 3):
            candidate = candidate.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        # Try each window on this day
        for (h, m_min, m_range) in windows:
            m = m_min + random.randint(0, m_range)
            slot = candidate.replace(hour=h, minute=m % 60, second=0, microsecond=0)
            if h == 10 and m >= 60:
                slot = slot.replace(hour=11, minute=m - 60)
            if slot > now:
                return slot.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

        # No window found today — move to start of next day
        candidate = candidate.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    # Fallback: next Tuesday at 08:30
    fallback = now.replace(hour=8, minute=30, second=0, microsecond=0) + timedelta(days=1)
    while fallback.weekday() not in (1, 2, 3):
        fallback += timedelta(days=1)
    return fallback.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


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
