import json
import os
import anthropic
from messaging.prompt_templates import LINKEDIN_DM_PROMPT, COLD_EMAIL_PROMPT, FOLLOWUP_PROMPT

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _clean(text: str) -> str:
    """Post-process generated text: remove em dashes, clean up spacing."""
    # Replace em dash variants with a comma or period depending on context
    text = text.replace(" — ", ", ")
    text = text.replace("— ", ". ")
    text = text.replace(" —", ".")
    text = text.replace("—", ", ")
    # Remove en dashes used mid-sentence
    text = text.replace(" – ", ", ")
    text = text.replace("– ", ". ")
    text = text.replace(" –", ".")
    return text.strip()


async def generate_linkedin_dm(target: dict) -> str:
    prompt = LINKEDIN_DM_PROMPT.format(
        contact_name=target.get("contact_name") or "there",
        contact_title=target.get("contact_title") or "",
        company_name=target["company_name"],
        context=target.get("notes") or "No additional context",
        tech_stack=", ".join(target.get("tech_stack") or []) or "Unknown",
        open_roles=target.get("open_role_url") or "None listed on website",
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return _clean(response.content[0].text)


async def generate_cold_email(target: dict) -> dict:
    prompt = COLD_EMAIL_PROMPT.format(
        contact_name=target.get("contact_name") or "there",
        contact_title=target.get("contact_title") or "",
        company_name=target["company_name"],
        context=target.get("notes") or "No additional context",
        tech_stack=", ".join(target.get("tech_stack") or []) or "Unknown",
        open_roles=target.get("open_role_url") or "None listed on website",
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        result = json.loads(raw)
        return {"subject": _clean(result.get("subject", "")), "body": _clean(result.get("body", ""))}
    except json.JSONDecodeError:
        lines = raw.split("\n")
        subject = lines[0].replace("Subject:", "").strip().strip('"')
        body = "\n".join(lines[1:]).strip()
        return {"subject": _clean(subject), "body": _clean(body)}


async def generate_followup(
    target: dict,
    original_message: str,
    channel: str,
    days_ago: int,
) -> str:
    prompt = FOLLOWUP_PROMPT.format(
        contact_name=target.get("contact_name") or "there",
        company_name=target["company_name"],
        channel=channel,
        days_ago=days_ago,
        original_message=original_message,
    )

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return _clean(response.content[0].text)
