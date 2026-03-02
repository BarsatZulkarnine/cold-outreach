import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/persona", tags=["persona"])

PERSONA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "persona.json")

DEFAULT_PERSONA = {
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


class PersonaUpdate(BaseModel):
    full_name: str
    short_name: str
    phone: str
    industry: str
    background: str
    tone_rules: str


def load_persona() -> dict:
    try:
        with open(PERSONA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_PERSONA


@router.get("")
async def get_persona():
    return load_persona()


@router.post("")
async def save_persona(req: PersonaUpdate):
    data = req.model_dump()
    try:
        with open(PERSONA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save persona: {e}")
    return {"saved": True, "persona": data}
