import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.schemas import (
    Target, Message, MessageOut,
    GenerateMessageRequest, BatchGenerateRequest, ApproveMessageRequest,
)
from messaging.message_gen import generate_linkedin_dm, generate_cold_email

router = APIRouter(prefix="/message", tags=["messaging"])


def _target_to_dict(target: Target) -> dict:
    return {
        "company_name": target.company_name,
        "contact_name": target.contact_name,
        "contact_title": target.contact_title,
        "notes": target.notes,
        "tech_stack": target.get_tech_stack(),
        "open_role_url": target.open_role_url,
    }


async def _generate_for_target(
    target: Target,
    channel: str,
    db: AsyncSession,
) -> Message:
    tdict = _target_to_dict(target)

    if channel == "linkedin":
        body = await generate_linkedin_dm(tdict)
        subject = None
    elif channel == "email":
        result = await generate_cold_email(tdict)
        body = result.get("body", "")
        subject = result.get("subject")
    else:
        raise ValueError(f"Unknown channel: {channel}")

    msg = Message(
        target_id=target.id,
        channel=channel,
        subject=subject,
        body=body,
        status="pending_approval",
        generated_at=datetime.utcnow(),
    )
    db.add(msg)

    # Update target status
    target.status = "message_generated"
    target.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(msg)
    return msg


@router.post("/generate/{target_id}")
async def generate_message(
    target_id: int,
    req: GenerateMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    if req.channel not in ("email", "linkedin"):
        raise HTTPException(status_code=400, detail="channel must be 'email' or 'linkedin'")

    print(f"[API] Generating {req.channel} message for target {target_id}: {target.company_name}")
    msg = await _generate_for_target(target, req.channel, db)

    return {
        "message_id": msg.id,
        "channel": msg.channel,
        "subject": msg.subject,
        "body": msg.body,
        "status": msg.status,
    }


@router.post("/generate/batch")
async def generate_batch(
    req: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    if req.channel not in ("email", "linkedin"):
        raise HTTPException(status_code=400, detail="channel must be 'email' or 'linkedin'")

    generated = 0
    errors = []

    for target_id in req.target_ids:
        result = await db.execute(select(Target).where(Target.id == target_id))
        target = result.scalar_one_or_none()
        if not target:
            errors.append({"target_id": target_id, "error": "not found"})
            continue

        try:
            await _generate_for_target(target, req.channel, db)
            generated += 1
            print(f"[API] Generated {req.channel} for {target.company_name}")
        except Exception as e:
            errors.append({"target_id": target_id, "error": str(e)})
            print(f"[API] Error generating message for target {target_id}: {e}")

    return {"generated": generated, "errors": errors}


@router.patch("/approve/{message_id}")
async def approve_message(
    message_id: int,
    req: ApproveMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.body = req.body
    if req.subject is not None:
        msg.subject = req.subject
    msg.status = "approved"
    await db.commit()

    return {"message_id": message_id, "status": "approved"}


@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    await db.delete(msg)
    await db.commit()

    return {"deleted": message_id}
