from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


async def check_followups():
    """
    Run daily at 9am. Find messages sent 6 days ago with no reply,
    generate follow-up messages, add them as pending_approval.
    Never auto-sends — requires manual approval in the Outreach tab.
    """
    from database import AsyncSessionLocal
    from models.schemas import Message, Target
    from messaging.message_gen import generate_followup
    from sqlalchemy import select

    print(f"[{datetime.utcnow().isoformat()}] [Scheduler] Running follow-up check...")

    six_days_ago_start = datetime.utcnow() - timedelta(days=7)
    six_days_ago_end = datetime.utcnow() - timedelta(days=6)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Message).where(
                Message.sent_at >= six_days_ago_start,
                Message.sent_at <= six_days_ago_end,
                Message.replied == False,
                Message.follow_up_sent == False,
                Message.status == "sent",
            )
        )
        messages = result.scalars().all()

        print(f"[Scheduler] Found {len(messages)} messages eligible for follow-up.")

        for msg in messages:
            try:
                target_result = await db.execute(
                    select(Target).where(Target.id == msg.target_id)
                )
                target = target_result.scalar_one_or_none()
                if not target:
                    continue

                days_ago = (datetime.utcnow() - msg.sent_at).days if msg.sent_at else 6
                followup_body = await generate_followup(
                    target={
                        "company_name": target.company_name,
                        "contact_name": target.contact_name,
                    },
                    original_message=msg.body,
                    channel=msg.channel,
                    days_ago=days_ago,
                )

                followup_msg = Message(
                    target_id=target.id,
                    channel=msg.channel,
                    subject=(f"Re: {msg.subject}" if msg.subject else None),
                    body=followup_body,
                    status="pending_approval",
                    generated_at=datetime.utcnow(),
                )
                db.add(followup_msg)

                # Mark original as follow_up_sent (pending — will be set to True after approval)
                msg.follow_up_sent = True
                msg.follow_up_sent_at = datetime.utcnow()

                await db.commit()
                print(f"[Scheduler] Follow-up queued for {target.company_name} (msg_id={msg.id})")

            except Exception as e:
                print(f"[Scheduler] Error generating follow-up for message {msg.id}: {e}")

    print(f"[{datetime.utcnow().isoformat()}] [Scheduler] Follow-up check complete.")


async def send_scheduled_emails():
    """
    Runs every 5 minutes. Finds approved email messages with scheduled_send_at <= now()
    and sends them. Respects daily limit. Never auto-sends unscheduled messages.
    """
    from database import AsyncSessionLocal
    from models.schemas import Message, Target
    from sending.email_sender import send_email, DailyLimitReachedError
    from sqlalchemy import select

    now = datetime.utcnow()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Message).where(
                Message.status == "approved",
                Message.channel == "email",
                Message.scheduled_send_at.isnot(None),
                Message.scheduled_send_at <= now,
                Message.sent_at.is_(None),
            )
        )
        messages = result.scalars().all()

        if not messages:
            return

        print(f"[{now.isoformat()}] [Scheduler] {len(messages)} scheduled email(s) due.")

        for msg in messages:
            try:
                target_result = await db.execute(select(Target).where(Target.id == msg.target_id))
                target = target_result.scalar_one_or_none()
                if not target or not target.contact_email:
                    print(f"[Scheduler] Skipping msg {msg.id} — no contact email.")
                    continue

                print(f"[Scheduler] Sending → {target.contact_email} ({target.company_name})")
                await send_email(
                    to_email=target.contact_email,
                    subject=msg.subject or "Quick note from Barsat",
                    body=msg.body,
                    message_id=msg.id,
                    db=db,
                )
            except DailyLimitReachedError as e:
                print(f"[Scheduler] Daily limit reached: {e}. Stopping.")
                break
            except Exception as e:
                print(f"[Scheduler] Error sending scheduled email {msg.id}: {e}")


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_followups,
        trigger=CronTrigger(hour=9, minute=0),
        id="followup_check",
        replace_existing=True,
        misfire_grace_time=3600,  # Run even if missed by up to 1 hour
    )
    scheduler.add_job(
        send_scheduled_emails,
        trigger=CronTrigger(minute="*/5"),  # Every 5 minutes
        id="scheduled_email_sender",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    return scheduler
