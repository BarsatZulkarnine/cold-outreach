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


def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_followups,
        trigger=CronTrigger(hour=9, minute=0),
        id="followup_check",
        replace_existing=True,
        misfire_grace_time=3600,  # Run even if missed by up to 1 hour
    )
    scheduler.start()
    return scheduler
