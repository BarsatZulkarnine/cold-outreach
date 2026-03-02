import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.schemas import (
    Target, TargetCreate, TargetOut, DiscoverMapsRequest, DiscoverLinkedInRequest,
)
from discovery.maps_scraper import scrape_google_maps
from discovery.website_parser import parse_website
from discovery.email_finder import find_email
from urllib.parse import urlparse

router = APIRouter(prefix="/discover", tags=["discovery"])


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url).netloc.lstrip("www.")
    except Exception:
        return None


async def _save_company(db: AsyncSession, company: dict) -> Target | None:
    """Persist a company dict to DB, skip if already exists by website."""
    website = company.get("company_website")

    # Check duplicate by website
    if website:
        existing = await db.execute(
            select(Target).where(Target.company_website == website)
        )
        if existing.scalar_one_or_none():
            return None

    # Also check by name
    existing_by_name = await db.execute(
        select(Target).where(Target.company_name == company["company_name"])
    )
    if existing_by_name.scalar_one_or_none():
        return None

    tech_stack = company.get("tech_stack") or []
    target = Target(
        source=company.get("source", "google_maps"),
        company_name=company["company_name"],
        company_website=website,
        company_size=company.get("company_size"),
        tech_stack=json.dumps(tech_stack),
        contact_name=company.get("contact_name"),
        contact_title=company.get("contact_title"),
        contact_email=company.get("contact_email"),
        linkedin_url=company.get("linkedin_url"),
        has_open_roles=company.get("has_open_roles", False),
        open_role_url=company.get("open_role_url"),
        notes=company.get("notes"),
        status="discovered",
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


@router.post("/maps")
async def discover_maps(
    req: DiscoverMapsRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run Google Maps scraper + website parser on results.
    Saves discovered companies to DB.
    """
    print(f"[API] POST /discover/maps — queries: {req.queries}, max_per_query: {req.max_per_query}")

    companies = await scrape_google_maps(
        queries=req.queries,
        max_results_per_query=req.max_per_query,
    )

    discovered = len(companies)
    saved = 0

    for company in companies:
        website = company.get("company_website")

        # Enrich with website parser
        if website:
            print(f"[API] Parsing website: {website}")
            try:
                parsed = await parse_website(website)
                if parsed["emails"]:
                    company["contact_email"] = parsed["emails"][0]
                if parsed["contacts"]:
                    top = parsed["contacts"][0]
                    company["contact_name"] = top["name"]
                    company["contact_title"] = top["title"]
                company["has_open_roles"] = parsed["has_open_roles"]
                company["open_role_url"] = parsed["open_role_url"]
                existing_tech = company.get("tech_stack") or []
                company["tech_stack"] = list(set(existing_tech + parsed["tech_hints"]))
                extra_notes = parsed["raw_notes"]
                if extra_notes:
                    company["notes"] = (company.get("notes") or "") + " | " + extra_notes
            except Exception as e:
                print(f"[API] Website parse error for {website}: {e}")

        target = await _save_company(db, company)
        if target:
            saved += 1
            print(f"[API] Saved: {company['company_name']} (id={target.id})")
        else:
            print(f"[API] Duplicate skipped: {company['company_name']}")

    return {"discovered": discovered, "saved": saved}


@router.post("/linkedin")
async def discover_linkedin(
    req: DiscoverLinkedInRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Run LinkedIn scraper. Saves discovered contacts to DB.
    LinkedIn scraper is built in Step 13 — returns 501 until then.
    """
    # Import here to avoid import errors if playwright isn't installed yet
    try:
        from discovery.linkedin_scraper import search_linkedin_contacts
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="LinkedIn scraper not yet available. Install playwright first.",
        )

    contacts = await search_linkedin_contacts(
        search_query=req.search_query,
        max_results=req.max_results,
    )

    saved = 0
    for contact in contacts:
        target = await _save_company(db, contact)
        if target:
            saved += 1

    return {"discovered": len(contacts), "saved": saved}


@router.post("/enrich/{target_id}")
async def enrich_target(
    target_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Run email finder on a specific target.
    Attempts Hunter.io + SMTP pattern guessing to find contact email.
    """
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    if target.contact_email:
        return {"message": "Already has email", "target": target}

    domain = _extract_domain(target.company_website)
    if not domain:
        raise HTTPException(status_code=400, detail="Target has no website to derive domain from")

    if not target.contact_name:
        raise HTTPException(status_code=400, detail="Target has no contact name to search for")

    parts = target.contact_name.strip().split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""

    print(f"[API] Enriching target {target_id}: {first} {last} @ {domain}")
    email = await find_email(first, last, domain)

    if email:
        target.contact_email = email
        target.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(target)
        print(f"[API] Email found: {email}")
    else:
        print(f"[API] No email found for target {target_id}")

    return {
        "target_id": target_id,
        "email_found": email,
        "contact_email": target.contact_email,
    }
