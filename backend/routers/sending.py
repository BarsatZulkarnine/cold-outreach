from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.schemas import Message, Target, BatchSendRequest
from sending.email_sender import send_email, DailyLimitReachedError, calculate_next_send_slot

router = APIRouter(prefix="/send", tags=["sending"])


@router.post("/email/{message_id}")
async def send_single_email(
    message_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Message must be approved before sending. Current status: {msg.status}",
        )

    if msg.channel != "email":
        raise HTTPException(status_code=400, detail="Not an email message")

    # Get target email
    target_result = await db.execute(select(Target).where(Target.id == msg.target_id))
    target = target_result.scalar_one_or_none()
    if not target or not target.contact_email:
        raise HTTPException(status_code=400, detail="Target has no contact email")

    try:
        success = await send_email(
            to_email=target.contact_email,
            subject=msg.subject or f"Quick note from Barsat",
            body=msg.body,
            message_id=message_id,
            db=db,
        )
    except DailyLimitReachedError as e:
        raise HTTPException(status_code=429, detail=str(e))

    if not success:
        raise HTTPException(status_code=500, detail="Email send failed")

    return {"sent": True, "message_id": message_id, "to": target.contact_email}


@router.post("/linkedin/{message_id}")
async def send_linkedin_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
):
    # LinkedIn sender is built in Step 14
    try:
        from sending.linkedin_sender import send_linkedin_dm
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="LinkedIn sender not yet available. Install playwright first.",
        )

    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Message must be approved before sending. Current status: {msg.status}",
        )

    target_result = await db.execute(select(Target).where(Target.id == msg.target_id))
    target = target_result.scalar_one_or_none()
    if not target or not target.linkedin_url:
        raise HTTPException(status_code=400, detail="Target has no LinkedIn URL")

    success = await send_linkedin_dm(
        profile_url=target.linkedin_url,
        message_body=msg.body,
        message_id=message_id,
        db=db,
    )

    if not success:
        raise HTTPException(status_code=500, detail="LinkedIn send failed")

    return {"sent": True, "message_id": message_id, "to": target.linkedin_url}


@router.post("/email/{message_id}/schedule")
async def schedule_single_email(
    message_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Schedule an approved email for the next optimal send slot (Tue–Thu, 8:30/10:30–12/5–6pm AEST)."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.status != "approved":
        raise HTTPException(status_code=400, detail=f"Message must be approved. Current status: {msg.status}")
    if msg.channel != "email":
        raise HTTPException(status_code=400, detail="Scheduling only supported for email messages")

    slot_utc = calculate_next_send_slot()
    msg.scheduled_send_at = slot_utc
    await db.commit()

    # Show Melbourne-local time in response
    tz = ZoneInfo("Australia/Melbourne")
    slot_local = slot_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    return {
        "scheduled": True,
        "message_id": message_id,
        "scheduled_for_utc": slot_utc.isoformat(),
        "scheduled_for_melbourne": slot_local.strftime("%a %d %b, %I:%M %p AEST"),
    }


@router.post("/batch/schedule")
async def schedule_batch_emails(
    req: BatchSendRequest,
    db: AsyncSession = Depends(get_db),
):
    """Schedule multiple approved email messages, staggered across optimal slots."""
    scheduled = 0
    failed = []
    offset = 0  # stagger messages by 15 minutes each

    for msg_id in req.message_ids:
        result = await db.execute(select(Message).where(Message.id == msg_id))
        msg = result.scalar_one_or_none()

        if not msg:
            failed.append({"message_id": msg_id, "error": "not found"})
            continue
        if msg.status != "approved":
            failed.append({"message_id": msg_id, "error": f"not approved (status: {msg.status})"})
            continue
        if msg.channel != "email":
            failed.append({"message_id": msg_id, "error": "not an email message"})
            continue

        slot_utc = calculate_next_send_slot(offset_minutes=offset)
        msg.scheduled_send_at = slot_utc
        scheduled += 1
        offset += 15  # 15-minute gap between scheduled sends

    await db.commit()
    return {"scheduled": scheduled, "failed": len(failed), "errors": failed}


@router.post("/batch")
async def send_batch(
    req: BatchSendRequest,
    db: AsyncSession = Depends(get_db),
):
    sent = 0
    failed = []

    for msg_id in req.message_ids:
        result = await db.execute(select(Message).where(Message.id == msg_id))
        msg = result.scalar_one_or_none()

        if not msg:
            failed.append({"message_id": msg_id, "error": "not found"})
            continue

        if msg.status != "approved":
            failed.append({"message_id": msg_id, "error": f"not approved (status: {msg.status})"})
            continue

        target_result = await db.execute(select(Target).where(Target.id == msg.target_id))
        target = target_result.scalar_one_or_none()

        try:
            if msg.channel == "email":
                if not target or not target.contact_email:
                    failed.append({"message_id": msg_id, "error": "no contact email"})
                    continue

                success = await send_email(
                    to_email=target.contact_email,
                    subject=msg.subject or "Quick note from Barsat",
                    body=msg.body,
                    message_id=msg_id,
                    db=db,
                )

            elif msg.channel == "linkedin":
                try:
                    from sending.linkedin_sender import send_linkedin_dm
                except ImportError:
                    failed.append({"message_id": msg_id, "error": "linkedin sender not installed"})
                    continue

                if not target or not target.linkedin_url:
                    failed.append({"message_id": msg_id, "error": "no linkedin url"})
                    continue

                success = await send_linkedin_dm(
                    profile_url=target.linkedin_url,
                    message_body=msg.body,
                    message_id=msg_id,
                    db=db,
                )
            else:
                failed.append({"message_id": msg_id, "error": f"unknown channel: {msg.channel}"})
                continue

            if success:
                sent += 1
            else:
                failed.append({"message_id": msg_id, "error": "send failed"})

        except DailyLimitReachedError as e:
            failed.append({"message_id": msg_id, "error": str(e)})
            break  # Stop batch if daily limit hit
        except Exception as e:
            failed.append({"message_id": msg_id, "error": str(e)})

    return {"sent": sent, "failed": len(failed), "errors": failed}
