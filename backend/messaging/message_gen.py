import json
import os
import anthropic
from messaging.prompt_templates import build_linkedin_dm_prompt, build_followup_prompt

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_PERSONA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "persona.json")

_DEFAULT_PERSONA = {
    "full_name": "Mohammed Barsat Zulkarnine",
    "short_name": "Barsat",
    "phone": "0475 128 013",
    "industry": "Software Engineering",
    "background": (
        "- Built real-time vehicle telemetry dashboard at Skyledge "
        "(Next.js, FastAPI, MongoDB, WebSockets, scikit-learn, Docker)\n"
        "- Interned at Nexobot building Vue.js components, CI/CD pipelines, route optimisation\n"
        "- Side projects: IoT EpiPen emergency alert system, cloud-deployed AI chatbot\n"
        "- Started coding in 6th grade, competed in Bangladesh national programming contest "
        "(reached finals twice in junior division), has a homelab\n"
        "- Visa: Temporary Graduate Visa, valid until Feb 2028, can work full-time anywhere in AU"
    ),
    "tone_rules": (
        "Direct and honest. Not formal. Not desperate.\n"
        'Hates buzzwords: never use "passionate about", "synergy", "leverage", '
        '"I hope this message finds you well", "hardworking team player", "excited to".\n'
        "Short sentences. No waffle. No padding.\n"
        'Sign off with just the short_name — no "Kind regards", no "Best wishes".'
    ),
}


def _load_persona() -> dict:
    try:
        with open(_PERSONA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _DEFAULT_PERSONA


def _clean(text: str) -> str:
    """Post-process generated text: remove em dashes, clean up spacing."""
    text = text.replace(" — ", ", ")
    text = text.replace("— ", ". ")
    text = text.replace(" —", ".")
    text = text.replace("—", ", ")
    text = text.replace(" – ", ", ")
    text = text.replace("– ", ". ")
    text = text.replace(" –", ".")
    return text.strip()


async def generate_linkedin_dm(target: dict) -> str:
    persona = _load_persona()
    prompt = build_linkedin_dm_prompt(persona, target)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return _clean(response.content[0].text)


_EMAIL_HIRING_SUBJECT = "junior dev – {company_name}"
_EMAIL_HIRING_BODY = """\
{greeting}

Saw {company_name} is looking for a developer. Just graduated from Swinburne with a software engineering degree (distinction, Dec 2025) and spent the past year at Skyledge as a grad dev — built a real-time vehicle telemetry dashboard from scratch (FastAPI, Next.js, MongoDB, WebSockets, Docker).

Would it make sense to have a quick chat?

Barsat
0475 128 013\
"""

_EMAIL_NOT_HIRING_SUBJECT = "junior dev – long shot"
_EMAIL_NOT_HIRING_BODY = """\
{greeting}

Nothing on {company_name}'s site at the moment, so this is speculative. Just graduated from Swinburne (software engineering, distinction, Dec 2025). Spent the past year at Skyledge building a real-time vehicle telemetry dashboard — FastAPI, Next.js, MongoDB, WebSockets, Docker.

Worth keeping in touch if something comes up?

Barsat
0475 128 013\
"""

# Words that indicate a scraped name is not actually a person's name
_BAD_NAME_TOKENS = {
    "customers", "client", "team", "staff", "admin", "manager", "hr",
    "recruit", "hiring", "contact", "support", "sales", "info", "hello",
    "enquir", "dear", "sir", "madam", "whom",
}


def _extract_first_name(raw: str | None) -> str | None:
    """
    Try to extract a usable first name from a potentially dirty scraped string.
    Returns None if the value looks like noise.
    """
    if not raw:
        return None
    raw = raw.strip()
    # Drop anything after common separators like '→', '|', '-', ','
    for sep in ("→", "|", " - ", ","):
        if sep in raw:
            raw = raw.split(sep)[0].strip()
    words = raw.split()
    if not words:
        return None
    first = words[0].lower()
    # Reject if first word matches known bad tokens
    if any(first.startswith(bad) for bad in _BAD_NAME_TOKENS):
        return None
    # Reject if looks like an email or URL
    if "@" in raw or "." in first:
        return None
    # Reject if more than 4 words (probably a title or garbage)
    if len(words) > 4:
        return None
    # Return just the first word (first name)
    return words[0].capitalize()


def _fill_email_template(subject_tmpl: str, body_tmpl: str, target: dict) -> dict:
    first_name = _extract_first_name(target.get("contact_name"))
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    company = target.get("company_name", "")
    subject = subject_tmpl.format(company_name=company)
    body = body_tmpl.format(company_name=company, greeting=greeting)
    return {"subject": subject, "body": body}


async def generate_cold_email(target: dict) -> dict:
    if target.get("has_open_roles"):
        return _fill_email_template(_EMAIL_HIRING_SUBJECT, _EMAIL_HIRING_BODY, target)
    return _fill_email_template(_EMAIL_NOT_HIRING_SUBJECT, _EMAIL_NOT_HIRING_BODY, target)


async def generate_followup(
    target: dict,
    original_message: str,
    channel: str,
    days_ago: int,
) -> str:
    persona = _load_persona()
    prompt = build_followup_prompt(persona, target, original_message, channel, days_ago)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return _clean(response.content[0].text)
