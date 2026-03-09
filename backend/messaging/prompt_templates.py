def build_persona_context(persona: dict) -> str:
    return (
        f"You are writing outreach messages on behalf of {persona['full_name']},\n"
        f"a {persona['industry']} professional based in Melbourne, Australia.\n"
        "\n"
        "Their background:\n"
        f"{persona['background']}\n"
        "\n"
        "Their voice and tone:\n"
        f"{persona['tone_rules']}\n"
        "\n"
        "Rules that ALWAYS apply:\n"
        "- Never start with \"I\" as the first word\n"
        "- Never be sycophantic (\"love what you're doing at X\")\n"
        "- One specific detail about the company/person — an observation, not a compliment\n"
        "- If there are no open roles, say so and ask anyway — be honest about it\n"
        "- Keep LinkedIn DMs under 80 words\n"
        "- Keep cold emails under 120 words (body only, not counting signature). Count carefully.\n"
        "- Never mention the word \"networking\"\n"
        "- NEVER use em dashes (\u2014). Use a full stop or comma instead. Em dashes are a giveaway.\n"
        "- No long paragraphs. Max 2 sentences per paragraph.\n"
        '- No rhetorical questions at the end ("Would love to connect!" etc.)'
    )


_LINKEDIN_DM_TEMPLATE = """

Write a LinkedIn DM to {contact_name} ({contact_title} at {company_name}).

Context about them/their company:
{context}

Their tech stack (if known): {tech_stack}

Open roles at their company: {open_roles}

Write a DM that:
1. Opens with one specific observation about the company (not generic praise)
2. One sentence: who {short_name} is and one concrete thing they built
3. The ask: clear, low-pressure, one sentence
4. Under 80 words total
5. Ends with just "{short_name}"

Output ONLY the message. No subject line. No explanation.
"""

_COLD_EMAIL_HIRING_TEMPLATE = """

Write a cold email to {contact_name} ({contact_title} at {company_name}).

They are ACTIVELY HIRING. Open role / careers page: {open_roles}

Context about them/their company:
{context}

Their tech stack (if known): {tech_stack}

Write:
1. A subject line (short, plain — e.g. "junior dev — worth a look?")
2. The email body

Body rules:
- Under 120 words. Be strict.
- First sentence: reference the specific role or careers page — be direct, not fawning.
- Second paragraph: one concrete project of {short_name}'s that matches their stack. One or two sentences.
- Final line: clear ask — apply? chat? keep it low-pressure.
- Signature (not counted in word limit):
  {short_name}
  {phone}
  (plain text only, no email address, no URLs, no links)

Output as JSON: {{"subject": "...", "body": "..."}}
The body should include the signature at the end.
"""

_COLD_EMAIL_NOT_HIRING_TEMPLATE = """

Write a cold email to {contact_name} ({contact_title} at {company_name}).

They are NOT actively hiring — no open roles listed on their site.

Context about them/their company:
{context}

Their tech stack (if known): {tech_stack}

Write:
1. A subject line (short, plain — e.g. "not sure if you're hiring, but...")
2. The email body

Body rules:
- Under 120 words. Be strict.
- First sentence: acknowledge there are no open roles — be upfront, don't pretend otherwise.
- Second paragraph: one concrete project of {short_name}'s relevant to their stack. One or two sentences.
- Final line: speculative ask — worth keeping in touch for when something opens up?
- Signature (not counted in word limit):
  {short_name}
  {phone}
  (plain text only, no email address, no URLs, no links)

Output as JSON: {{"subject": "...", "body": "..."}}
The body should include the signature at the end.
"""

_FOLLOWUP_TEMPLATE = """

Write a follow-up message to {contact_name} at {company_name}.
This is a follow-up to a {channel} sent {days_ago} days ago with no reply.

Original message sent:
{original_message}

Rules:
- 2-3 sentences max
- Not passive-aggressive, not grovelling
- Acknowledge they're busy. Leave the door open.
- One new angle if possible (e.g. a recent project or update)
- For LinkedIn: under 40 words. For email: under 60 words.

Output ONLY the message.
"""


def build_linkedin_dm_prompt(persona: dict, target: dict) -> str:
    return (build_persona_context(persona) + _LINKEDIN_DM_TEMPLATE).format(
        contact_name=target.get("contact_name") or "there",
        contact_title=target.get("contact_title") or "",
        company_name=target["company_name"],
        context=target.get("notes") or "No additional context",
        tech_stack=", ".join(target.get("tech_stack") or []) or "Unknown",
        open_roles=target.get("open_role_url") or "None listed on website",
        short_name=persona.get("short_name", "there"),
    )


def build_cold_email_prompt(persona: dict, target: dict) -> str:
    is_hiring = bool(target.get("has_open_roles"))
    template = _COLD_EMAIL_HIRING_TEMPLATE if is_hiring else _COLD_EMAIL_NOT_HIRING_TEMPLATE
    return (build_persona_context(persona) + template).format(
        contact_name=target.get("contact_name") or "there",
        contact_title=target.get("contact_title") or "",
        company_name=target["company_name"],
        context=target.get("notes") or "No additional context",
        tech_stack=", ".join(target.get("tech_stack") or []) or "Unknown",
        open_roles=target.get("open_role_url") or "careers page",
        short_name=persona.get("short_name", "there"),
        phone=persona.get("phone", ""),
    )


def build_followup_prompt(persona: dict, target: dict, original_message: str, channel: str, days_ago: int) -> str:
    return (build_persona_context(persona) + _FOLLOWUP_TEMPLATE).format(
        contact_name=target.get("contact_name") or "there",
        company_name=target["company_name"],
        channel=channel,
        days_ago=days_ago,
        original_message=original_message,
    )
