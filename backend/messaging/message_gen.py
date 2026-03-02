import json
import os
import anthropic
from messaging.prompt_templates import build_linkedin_dm_prompt, build_cold_email_prompt, build_followup_prompt

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


async def generate_cold_email(target: dict) -> dict:
    persona = _load_persona()
    prompt = build_cold_email_prompt(persona, target)

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
    persona = _load_persona()
    prompt = build_followup_prompt(persona, target, original_message, channel, days_ago)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return _clean(response.content[0].text)
