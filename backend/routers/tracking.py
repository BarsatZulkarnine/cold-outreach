from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models.schemas import Target, Message, TargetUpdate, TargetWithMessages, StatsOut

router = APIRouter(prefix="/targets", tags=["tracking"])


@router.get("")
async def list_targets(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    has_email: Optional[bool] = Query(None),
    has_linkedin: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Target)

    if status:
        query = query.where(Target.status == status)
    if source:
        query = query.where(Target.source == source)
    if has_email is True:
        query = query.where(Target.contact_email.isnot(None))
    if has_email is False:
        query = query.where(Target.contact_email.is_(None))
    if has_linkedin is True:
        query = query.where(Target.linkedin_url.isnot(None))
    if has_linkedin is False:
        query = query.where(Target.linkedin_url.is_(None))

    # Total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Paginate
    query = query.offset((page - 1) * limit).limit(limit).order_by(Target.created_at.desc())
    result = await db.execute(query)
    targets = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": t.id,
                "source": t.source,
                "company_name": t.company_name,
                "company_website": t.company_website,
                "contact_name": t.contact_name,
                "contact_title": t.contact_title,
                "contact_email": t.contact_email,
                "linkedin_url": t.linkedin_url,
                "has_open_roles": t.has_open_roles,
                "tech_stack": t.get_tech_stack(),
                "status": t.status,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in targets
        ],
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Target))
    targets = result.scalars().all()

    by_status: dict[str, int] = {}
    for t in targets:
        by_status[t.status] = by_status.get(t.status, 0) + 1

    total = len(targets)
    replied = by_status.get("replied", 0) + by_status.get("meeting", 0)

    # Count sent messages by channel
    msgs_result = await db.execute(
        select(Message).where(Message.sent_at.isnot(None))
    )
    sent_msgs = msgs_result.scalars().all()
    emails_sent = sum(1 for m in sent_msgs if m.channel == "email")
    linkedin_sent = sum(1 for m in sent_msgs if m.channel == "linkedin")

    meetings = by_status.get("meeting", 0)
    total_sent = emails_sent + linkedin_sent
    reply_rate = round(replied / total_sent, 4) if total_sent > 0 else 0.0

    return {
        "total_discovered": total,
        "emails_sent": emails_sent,
        "linkedin_sent": linkedin_sent,
        "replied": replied,
        "meetings": meetings,
        "reply_rate": reply_rate,
        "by_status": by_status,
    }


@router.get("/{target_id}")
async def get_target(
    target_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    msgs_result = await db.execute(
        select(Message).where(Message.target_id == target_id).order_by(Message.generated_at.desc())
    )
    messages = msgs_result.scalars().all()

    return {
        "id": target.id,
        "source": target.source,
        "company_name": target.company_name,
        "company_website": target.company_website,
        "company_size": target.company_size,
        "tech_stack": target.get_tech_stack(),
        "contact_name": target.contact_name,
        "contact_title": target.contact_title,
        "contact_email": target.contact_email,
        "linkedin_url": target.linkedin_url,
        "has_open_roles": target.has_open_roles,
        "open_role_url": target.open_role_url,
        "notes": target.notes,
        "status": target.status,
        "created_at": target.created_at,
        "updated_at": target.updated_at,
        "messages": [
            {
                "id": m.id,
                "channel": m.channel,
                "subject": m.subject,
                "body": m.body,
                "status": m.status,
                "generated_at": m.generated_at,
                "sent_at": m.sent_at,
                "opened": m.opened,
                "replied": m.replied,
                "follow_up_sent": m.follow_up_sent,
            }
            for m in messages
        ],
    }


@router.patch("/{target_id}")
async def update_target(
    target_id: int,
    req: TargetUpdate,
    db: AsyncSession = Depends(get_db),
):
    import json

    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    update_data = req.model_dump(exclude_none=True)
    for field, value in update_data.items():
        if field == "tech_stack":
            target.tech_stack = json.dumps(value)
        else:
            setattr(target, field, value)

    target.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(target)

    return {"target_id": target_id, "status": target.status, "updated": list(update_data.keys())}
