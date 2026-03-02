# Cold Outreach Bot — Claude Code Build Instructions

## Project Overview

Build an automated cold outreach system to help a junior software engineer (Barsat) land a job in Australia. The system discovers target companies via Google Maps and LinkedIn, finds contact details, generates personalized non-AI-sounding messages using the Anthropic API, sends them via email and LinkedIn, and tracks everything in a dashboard.

This is a **Python backend (FastAPI) + React frontend** project. Build it as a standalone repo — do NOT modify any existing jobFinder codebase.

---

## Persona — Inject Into Every Message Generation Call

This is the persona object to pass into Claude when generating messages. Never deviate from this voice.

```json
{
  "name": "Barsat",
  "full_name": "Mohammed Barsat Zulkarnine",
  "email": "mohammedbarsatzulkarnine@gmail.com",
  "phone": "0475128013",
  "github": "https://github.com/BarsatZulkarnine",
  "visa": "Temporary Graduate Visa (valid until Feb 2028) — can work full-time, no PR/citizenship needed",
  "education": "BEng Software Engineering (Hons), Swinburne University, Dec 2025, Distinction",
  "experience": [
    "Graduate SWE at Skyledge — built full-stack vehicle telemetry dashboard (Next.js, FastAPI, MongoDB, WebSockets, scikit-learn, Docker)",
    "Intern at Nexobot — Vue.js components, CI/CD via Bitbucket, route optimisation with map APIs, Docker"
  ],
  "projects": [
    "EpiPen Emergency Alert System — ESP32 + Python + Telegram API + OpenAI API + React + Firebase",
    "Cloud-deployed Library Management System — AWS EC2, ALB, Auto Scaling, GitHub Actions",
    "AI Conversational Assistant — Node.js, PostgreSQL, Redis, OpenAI API, Docker",
    "The Jaunt Store (freelance) — Next.js, Vercel"
  ],
  "skills": ["Python", "TypeScript", "React", "Next.js", "Vue.js", "FastAPI", "Node.js", "AWS", "Docker", "PostgreSQL", "MongoDB", "Redis", "WebSockets", "CI/CD"],
  "backstory": "Started coding in 6th grade with game dev. Competed in Bangladesh National Programming Contest, reached finals twice in junior division. Self-directed learner, always has a side project. Has a homelab.",
  "personality": "frank, direct, not formal. Hates buzzwords. Approachable, real. Introvert who can hold a conversation.",
  "tone_rules": [
    "Sound like a tired but sharp grad — not a recruiter",
    "Never use: 'passionate about', 'synergy', 'I hope this finds you well', 'hardworking team player'",
    "Use specific project details when relevant",
    "Short clear sentences. No waffle.",
    "Genuine curiosity about the role/company — not flattery",
    "Sign off as: Barsat"
  ]
}
```

---

## Project Structure

```
cold-outreach-bot/
│
├── backend/
│   ├── main.py                        # FastAPI app entry point
│   ├── config.py                      # Env vars, constants
│   ├── database.py                    # SQLite (dev) / PostgreSQL (prod) setup via SQLAlchemy
│   │
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── maps_scraper.py            # Google Maps → company list
│   │   ├── website_parser.py          # Scrape company websites for emails + contacts
│   │   ├── linkedin_scraper.py        # Playwright LinkedIn profile/company scraper
│   │   └── email_finder.py            # Hunter.io API + pattern guessing
│   │
│   ├── enrichment/
│   │   ├── __init__.py
│   │   └── tech_stack_detector.py     # Detect tech stack from website (Wappalyzer-style)
│   │
│   ├── messaging/
│   │   ├── __init__.py
│   │   ├── message_gen.py             # Anthropic API calls — generates DMs + emails
│   │   └── prompt_templates.py        # System prompts with Barsat's persona baked in
│   │
│   ├── sending/
│   │   ├── __init__.py
│   │   ├── email_sender.py            # Gmail API (OAuth2) — send + track
│   │   └── linkedin_sender.py         # Playwright — connection request + DM
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── followup_scheduler.py      # APScheduler — auto follow-up after 6 days
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py                 # SQLAlchemy models + Pydantic schemas
│   │
│   └── routers/
│       ├── __init__.py
│       ├── discovery.py               # POST /discover/maps, POST /discover/linkedin
│       ├── messaging.py               # POST /message/generate, POST /message/approve
│       ├── sending.py                 # POST /send/email, POST /send/linkedin
│       └── tracking.py               # GET /targets, GET /stats, PATCH /target/{id}
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx          # Stats overview
│   │   │   ├── Targets.tsx            # Table of all discovered targets
│   │   │   ├── Outreach.tsx           # Review + approve messages before sending
│   │   │   └── Settings.tsx           # API keys, Gmail auth, LinkedIn creds
│   │   ├── components/
│   │   │   ├── TargetCard.tsx
│   │   │   ├── MessagePreview.tsx
│   │   │   ├── StatsBar.tsx
│   │   │   └── StatusBadge.tsx
│   │   └── api/
│   │       └── client.ts              # Axios client pointing to FastAPI
│   ├── package.json
│   └── vite.config.ts
│
├── .env.example
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## Database Schema

Use SQLAlchemy ORM. Start with SQLite (`outreach.db`) for development, config should support swapping to PostgreSQL.

### Table: `targets`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| source | TEXT | `"google_maps"` or `"linkedin"` |
| company_name | TEXT | |
| company_website | TEXT | |
| company_size | TEXT | e.g. `"11-50"` |
| tech_stack | JSON | list of detected techs |
| contact_name | TEXT | |
| contact_title | TEXT | e.g. `"Engineering Manager"` |
| contact_email | TEXT | nullable |
| linkedin_url | TEXT | nullable |
| has_open_roles | BOOLEAN | scraped from careers page |
| open_role_url | TEXT | nullable |
| notes | TEXT | anything scraped that might help personalize |
| status | TEXT | `"discovered"` → `"message_generated"` → `"approved"` → `"sent"` → `"replied"` → `"meeting"` → `"rejected"` |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### Table: `messages`

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| target_id | INTEGER FK → targets.id | |
| channel | TEXT | `"email"` or `"linkedin"` |
| subject | TEXT | nullable (email only) |
| body | TEXT | |
| generated_at | DATETIME | |
| sent_at | DATETIME | nullable |
| opened | BOOLEAN | email only |
| replied | BOOLEAN | |
| follow_up_sent | BOOLEAN | default false |
| follow_up_sent_at | DATETIME | nullable |

---

## Module-by-Module Instructions

---

### 1. `discovery/maps_scraper.py`

**Goal:** Search Google Maps for tech companies in Melbourne, return structured company data.

**Implementation:**
- Use `googlemaps` Python SDK (requires `GOOGLE_MAPS_API_KEY` in `.env`)
- Use `places_nearby` or `text_search` with queries like:
  - `"software company Melbourne VIC"`
  - `"IT company Melbourne"`
  - `"tech startup Melbourne"`
  - `"software development company Cremorne"` (Melbourne tech suburb)
  - `"software development company Richmond"`
  - `"software development company Collingwood"`
  - `"SaaS company Melbourne"`
- For each result extract: `name`, `website`, `formatted_address`, `phone_number`, `place_id`, `rating`, `user_ratings_total`
- Filter out: companies with <3 reviews, non-tech categories, mining/oil/gas keywords in name
- Deduplicate by website domain
- Return list of dicts — do NOT hit the DB here, let the router handle persistence

**Rate limiting:** Add `asyncio.sleep(0.5)` between API calls.

**Function signature:**
```python
async def scrape_google_maps(queries: list[str], max_results_per_query: int = 20) -> list[dict]:
    ...
```

---

### 2. `discovery/website_parser.py`

**Goal:** Given a company website URL, extract contact emails, team member names/titles, and careers page info.

**Implementation:**
- Use `httpx` for async HTTP requests with a realistic User-Agent header
- Use `BeautifulSoup4` for HTML parsing
- **Email extraction:**
  - Regex scan all page text for email patterns
  - Check `/contact`, `/about`, `/team`, `/careers`, `/jobs` paths
  - Priority: emails containing `cto`, `tech`, `engineering`, `dev`, `hi`, `hello`, `info`
  - Avoid: `noreply`, `support@`, `privacy@`
- **Contact name extraction:**
  - Look for `<title>` + name patterns on `/team` or `/about` pages
  - Extract names with titles matching: `CTO`, `CEO`, `Head of Engineering`, `Tech Lead`, `Software Engineer`, `Engineering Manager`, `VP Engineering`
- **Careers page detection:**
  - Check for `/careers`, `/jobs`, `/work-with-us`, `/join-us`
  - If found, scan for keywords: `engineer`, `developer`, `software`, `junior`, `graduate`, `entry`
  - Store `has_open_roles=True` if junior/grad roles found, `has_open_roles=False` otherwise
- **Tech stack hints:**
  - Look for meta tags, script src attributes, footer text
  - Common detectable: React, Vue, Angular, Next.js, Django, Rails, Laravel, AWS, Heroku

**Function signature:**
```python
async def parse_website(url: str) -> dict:
    # Returns: {emails, contacts, has_open_roles, open_role_url, tech_hints, raw_notes}
```

---

### 3. `discovery/email_finder.py`

**Goal:** Given a person's name and company domain, find or guess their email.

**Implementation — two strategies:**

**Strategy A — Hunter.io API:**
```python
async def hunter_find(first_name: str, last_name: str, domain: str) -> str | None:
    # GET https://api.hunter.io/v2/email-finder
    # params: first_name, last_name, domain, api_key=HUNTER_API_KEY
    # returns email if confidence > 70, else None
```

**Strategy B — Pattern guessing + SMTP verification:**
```python
PATTERNS = [
    "{first}.{last}@{domain}",
    "{first}@{domain}",
    "{first}{last}@{domain}",
    "{f}{last}@{domain}",      # e.g. jsmith@
    "{first}.{l}@{domain}",    # e.g. john.s@
]

async def guess_email(first_name: str, last_name: str, domain: str) -> str | None:
    # Try each pattern
    # For each candidate email, do lightweight SMTP RCPT TO check
    # (connect to MX server, EHLO, MAIL FROM: verify@check.com, RCPT TO: candidate)
    # Return first that doesn't get 550 reject
    # Wrap in try/except — many servers block this, that's fine
```

Use Strategy A first, fall back to Strategy B, fall back to `None` (will use contact form instead).

---

### 4. `discovery/linkedin_scraper.py`

**Goal:** Search LinkedIn for engineering managers, tech leads, CTOs at Melbourne companies. Extract profile data for personalization.

**IMPORTANT — LinkedIn blocks bots. Implement carefully:**

- Use `playwright` with `playwright-stealth` (`pip install playwright-stealth`)
- Launch in **non-headless mode** initially so user can solve CAPTCHAs manually
- Add config flag `LINKEDIN_HEADLESS=false` in `.env`
- Store cookies after first login in `linkedin_cookies.json`, reuse on subsequent runs
- **Never hardcode credentials** — read from `.env`: `LINKEDIN_EMAIL`, `LINKEDIN_PASSWORD`

**Search flow:**
```
1. Navigate to linkedin.com/search/results/people/
2. Params: keywords="Engineering Manager" OR "CTO" OR "Tech Lead", 
           location="Melbourne, Victoria, Australia",
           company size filter: 11-200 employees
3. For each result (max 15 per session):
   - Extract: name, title, company, profile URL, snippet text
4. Navigate to each profile (max 5 per session — don't be greedy)
   - Extract: about section, recent activity (posts), skills, current company details
5. Sleep 3-7 minutes between profile visits (random)
```

**HARD LIMITS — enforce in code:**
```python
MAX_PROFILES_PER_SESSION = 5
MAX_SEARCHES_PER_DAY = 3
MIN_DELAY_BETWEEN_ACTIONS_SEC = 180   # 3 minutes
MAX_DELAY_BETWEEN_ACTIONS_SEC = 420   # 7 minutes
```

Store last run time in `linkedin_rate_limit.json`. If called again within 2 hours, raise `RateLimitError`.

**Function signature:**
```python
async def search_linkedin_contacts(
    search_query: str,
    location: str = "Melbourne, Victoria, Australia",
    max_results: int = 15
) -> list[dict]:
```

---

### 5. `messaging/prompt_templates.py`

**Goal:** Define the system prompts that make messages sound like Barsat, not a bot.

```python
PERSONA_CONTEXT = """
You are writing outreach messages on behalf of Barsat (Mohammed Barsat Zulkarnine), 
a recent software engineering grad from Swinburne University (Dec 2025, Distinction) 
based in Melbourne, Australia.

His background:
- Built a real-time vehicle telemetry dashboard at Skyledge (Next.js, FastAPI, MongoDB, 
  WebSockets, scikit-learn, Docker)
- Interned at Nexobot building Vue.js components, CI/CD pipelines, route optimisation
- Side projects include an IoT EpiPen emergency alert system and a cloud-deployed 
  AI chatbot
- Started coding in 6th grade, competed in Bangladesh's national programming contest 
  (reached finals twice in junior division), has a homelab
- Visa: Temporary Graduate Visa, valid until Feb 2028, can work full-time anywhere in AU

His voice:
- Direct and honest. Not formal. Not desperate.
- Hates buzzwords — NEVER write: "passionate about", "synergy", "leverage", 
  "I hope this message finds you well", "hardworking team player", "excited to"
- Short sentences. No waffle. No padding.
- Sounds like a message written at 11pm after a long day — genuine, a bit casual, 
  specific
- Sign off: just "Barsat" — no "Kind regards", no "Best wishes"

Rules:
- Never start with "I" as the first word
- Never be sycophantic ("love what you're doing at X")
- One specific detail about the company/person — an observation, not a compliment
- If there are no open roles, say so and ask anyway — be honest about it
- Keep LinkedIn DMs under 100 words
- Keep cold emails under 150 words
- Never mention the word "networking"
"""

LINKEDIN_DM_PROMPT = PERSONA_CONTEXT + """

Write a LinkedIn DM to {contact_name} ({contact_title} at {company_name}).

Context about them/their company:
{context}

Their tech stack (if known): {tech_stack}

Open roles at their company: {open_roles}

Write a DM that:
1. Opens with something specific (not generic praise)
2. States who Barsat is in one sentence — be concrete, not vague
3. Makes the ask clearly but low-pressure
4. Is under 100 words
5. Ends with just "– Barsat"

Output ONLY the message. No subject line. No explanation.
"""

COLD_EMAIL_PROMPT = PERSONA_CONTEXT + """

Write a cold email to {contact_name} ({contact_title} at {company_name}).

Context about them/their company:
{context}

Their tech stack (if known): {tech_stack}

Open roles at their company: {open_roles}

Write:
1. A subject line (short, specific, non-clickbait — e.g. "Junior dev — worth 10 mins?")
2. The email body

Rules:
- Under 150 words
- Opens with something specific about their company (not a compliment — an observation)
- One relevant project of Barsat's that matches their stack
- Clear low-pressure ask at the end
- Signature: "Barsat\\nmohammedbarsatzulkarnine@gmail.com | 0475 128 013 | github.com/BarsatZulkarnine"

Output as JSON: {"subject": "...", "body": "..."}
"""

FOLLOWUP_PROMPT = PERSONA_CONTEXT + """

Write a follow-up message to {contact_name} at {company_name}.
This is a follow-up to a {channel} sent {days_ago} days ago with no reply.

Original message sent:
{original_message}

Rules:
- 2-3 sentences max
- Not passive-aggressive, not grovelling
- Just checking in, acknowledging they're busy, leaving door open
- One new piece of info or angle if possible (e.g. a project update)
- For LinkedIn: under 50 words. For email: under 80 words.

Output ONLY the message.
"""
```

---

### 6. `messaging/message_gen.py`

**Goal:** Call Anthropic API to generate personalized messages.

```python
import anthropic
from .prompt_templates import LINKEDIN_DM_PROMPT, COLD_EMAIL_PROMPT, FOLLOWUP_PROMPT
import json

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def generate_linkedin_dm(target: dict) -> str:
    prompt = LINKEDIN_DM_PROMPT.format(
        contact_name=target.get("contact_name", "there"),
        contact_title=target.get("contact_title", ""),
        company_name=target["company_name"],
        context=target.get("notes", "No additional context"),
        tech_stack=", ".join(target.get("tech_stack", [])) or "Unknown",
        open_roles=target.get("open_role_url", "None listed on website")
    )
    
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


async def generate_cold_email(target: dict) -> dict:
    prompt = COLD_EMAIL_PROMPT.format(
        contact_name=target.get("contact_name", "there"),
        contact_title=target.get("contact_title", ""),
        company_name=target["company_name"],
        context=target.get("notes", "No additional context"),
        tech_stack=", ".join(target.get("tech_stack", [])) or "Unknown",
        open_roles=target.get("open_role_url", "None listed on website")
    )
    
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response.content[0].text.strip()
    # Parse JSON output
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: extract subject from first line
        lines = raw.split("\n")
        return {"subject": lines[0].replace("Subject:", "").strip(), "body": "\n".join(lines[1:]).strip()}


async def generate_followup(target: dict, original_message: str, channel: str, days_ago: int) -> str:
    prompt = FOLLOWUP_PROMPT.format(
        contact_name=target.get("contact_name", "there"),
        company_name=target["company_name"],
        channel=channel,
        days_ago=days_ago,
        original_message=original_message
    )
    
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()
```

---

### 7. `sending/email_sender.py`

**Goal:** Send emails via Gmail API with OAuth2. Track sends.

**Setup:**
- Use `google-auth`, `google-auth-oauthlib`, `google-api-python-client`
- OAuth2 flow: on first run, open browser for Gmail auth, save `gmail_token.json`
- Required scope: `https://www.googleapis.com/auth/gmail.send`
- Instructions for getting credentials: Create OAuth2 app in Google Cloud Console, download `credentials.json`, place in project root

**Implementation:**
```python
async def send_email(
    to_email: str,
    subject: str,
    body: str,
    target_id: int
) -> bool:
    # Build MIMEText message
    # Send via gmail.users().messages().send()
    # On success: update messages table (sent_at = now)
    # Add random delay: asyncio.sleep(random.uniform(30, 90))
    # Return True/False
```

**Throttling — enforce in code:**
```python
MAX_EMAILS_PER_DAY = 40
# Track sends in DB, check count before each send
# If limit hit: raise DailyLimitReachedError
```

---

### 8. `sending/linkedin_sender.py`

**Goal:** Send LinkedIn connection requests and DMs via Playwright.

**CRITICAL — account safety rules (enforce in code, not just comments):**

```python
MAX_CONNECTION_REQUESTS_PER_DAY = 15
MAX_DMS_PER_DAY = 10
MIN_DELAY_BETWEEN_SENDS_SEC = 120    # 2 minutes
MAX_DELAY_BETWEEN_SENDS_SEC = 300    # 5 minutes

# Track in linkedin_daily_counts.json:
# { "date": "2025-01-15", "connection_requests": 0, "dms": 0 }
# Reset on new date
```

**Flow:**
```
For connection request:
1. Navigate to profile URL
2. Click Connect button (if not already connected)
3. Add note: use generated DM text (truncated to 200 chars if needed)
4. Click Send
5. Sleep random delay

For DM to existing connection:
1. Navigate to profile URL  
2. Click Message button
3. Type message (simulate typing: random delay between keystrokes)
4. Click Send
5. Sleep random delay
```

**Error handling:**
- If "Connect" button not found → profile already connected or premium only → log and skip
- If captcha detected → pause, alert user via console log, wait for manual intervention
- If 429/rate limit page → stop all LinkedIn operations for 24 hours, set flag in `linkedin_rate_limit.json`

---

### 9. `scheduler/followup_scheduler.py`

**Goal:** Check daily for targets that need a follow-up.

- Use `APScheduler` with `AsyncIOScheduler`
- Run daily at 9:00 AM
- Query DB for messages where:
  - `sent_at` is 6 days ago
  - `replied = False`
  - `follow_up_sent = False`
  - `channel` is `email` or `linkedin`
- For each: generate follow-up message via `message_gen.generate_followup()`
- Add to messages table with status `"pending_approval"` — do NOT auto-send follow-ups
- Frontend shows them in the Outreach tab for manual approval

---

### 10. FastAPI Routers

#### `routers/discovery.py`
```
POST /discover/maps
  body: { queries: list[str], max_per_query: int }
  → runs maps_scraper, runs website_parser on each result, saves to DB
  → returns: { discovered: int, saved: int }

POST /discover/linkedin  
  body: { search_query: str, max_results: int }
  → runs linkedin_scraper, saves to DB
  → returns: { discovered: int }

POST /discover/enrich/{target_id}
  → runs email_finder on a specific target
  → updates target in DB
  → returns updated target
```

#### `routers/messaging.py`
```
POST /message/generate/{target_id}
  body: { channel: "email" | "linkedin" }
  → generates message via message_gen
  → saves to messages table with status "pending_approval"
  → returns generated message

POST /message/generate/batch
  body: { target_ids: list[int], channel: "email" | "linkedin" }
  → generates messages for all targets
  → returns { generated: int }

PATCH /message/approve/{message_id}
  body: { body: str, subject: str | None }  (user can edit before approving)
  → sets message status to "approved"

DELETE /message/{message_id}
  → deletes message (user rejected it)
```

#### `routers/sending.py`
```
POST /send/email/{message_id}
  → sends approved email
  → updates message sent_at

POST /send/linkedin/{message_id}
  → sends approved LinkedIn DM/connection request
  → updates message sent_at

POST /send/batch
  body: { message_ids: list[int] }
  → sends all approved messages (with throttling)
  → returns { sent: int, failed: int }
```

#### `routers/tracking.py`
```
GET /targets
  params: status, source, has_email, has_linkedin, page, limit
  → paginated list of targets

GET /targets/{id}
  → single target with all messages

PATCH /targets/{id}
  body: { status, notes, contact_name, contact_email, etc. }
  → manual update (e.g. mark as replied after seeing email response)

GET /stats
  → returns:
  {
    total_discovered: int,
    emails_sent: int,
    linkedin_sent: int, 
    replied: int,
    meetings: int,
    reply_rate: float,
    by_status: { ... }
  }
```

---

### 11. Frontend

Use **React + TypeScript + Vite + TailwindCSS**.

#### Pages:

**Dashboard (`/`)**
- Stats bar: Discovered → Messages Generated → Sent → Replied → Meeting
- Funnel chart (use Recharts)
- Recent activity feed (last 10 actions)

**Targets (`/targets`)**
- Table with columns: Company, Contact, Source, Tech Stack, Has Roles, Status, Actions
- Filter bar: by status, source, has_email
- Each row: click to expand → show all scraped info + messages
- Action buttons per row: "Generate Message", "View Messages"
- Inline status badge with color coding:
  - `discovered` → grey
  - `message_generated` → blue
  - `approved` → yellow
  - `sent` → purple
  - `replied` → green
  - `meeting` → bright green
  - `rejected` → red

**Outreach (`/outreach`)**
- Shows all messages in `pending_approval` status
- Message preview card: shows contact name, company, channel badge, message body
- Edit box below each message (user can tweak before approving)
- Buttons: ✅ Approve | ✏️ Edit | ❌ Delete
- Approved messages queue: shows approved messages ready to send
- "Send All Approved" button (with confirmation dialog showing count)

**Settings (`/settings`)**
- API key inputs: `GOOGLE_MAPS_API_KEY`, `HUNTER_API_KEY`, `ANTHROPIC_API_KEY`
- Gmail auth: "Connect Gmail" button → triggers OAuth flow
- LinkedIn: email + password input (stored in `.env`, not DB)
- Daily limits config: max emails/day, max LinkedIn/day
- Export button: download all targets + messages as CSV

---

## Environment Variables

Create `.env.example` with these keys (no values):

```
# Anthropic
ANTHROPIC_API_KEY=

# Google
GOOGLE_MAPS_API_KEY=

# Hunter.io (email finder)
HUNTER_API_KEY=

# Gmail OAuth (download credentials.json from Google Cloud Console)
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=gmail_token.json

# LinkedIn (used by Playwright — never sent to any API)
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=
LINKEDIN_HEADLESS=false
LINKEDIN_COOKIES_PATH=linkedin_cookies.json

# Database
DATABASE_URL=sqlite:///./outreach.db

# App
BACKEND_PORT=8001
FRONTEND_PORT=5174
```

---

## `requirements.txt`

```
fastapi
uvicorn[standard]
sqlalchemy
aiosqlite
httpx
beautifulsoup4
playwright
playwright-stealth
googlemaps
anthropic
google-auth
google-auth-oauthlib
google-api-python-client
apscheduler
python-dotenv
pydantic
pydantic-settings
```

---

## `docker-compose.yml`

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8001:8001"
    volumes:
      - ./.env:/app/.env
      - ./outreach.db:/app/outreach.db
      - ./gmail_token.json:/app/gmail_token.json
      - ./linkedin_cookies.json:/app/linkedin_cookies.json
    environment:
      - DATABASE_URL=sqlite:///./outreach.db

  frontend:
    build: ./frontend
    ports:
      - "5174:5174"
    depends_on:
      - backend
```

Note: LinkedIn Playwright requires a display. For local dev, run backend directly (`uvicorn main:app`), not in Docker. Docker is for email + Maps + message gen only.

---

## Build Order — Do This Sequence

Claude Code: build in this exact order. Each step should be independently runnable before moving to the next.

```
Step 1:  models/schemas.py + database.py           — DB setup, all tables
Step 2:  discovery/maps_scraper.py                 — Google Maps → company list  
Step 3:  discovery/website_parser.py               — Website → emails + contacts
Step 4:  discovery/email_finder.py                 — Hunter.io + SMTP guessing
Step 5:  routers/discovery.py                      — Wire steps 2-4 to API endpoints
Step 6:  messaging/prompt_templates.py             — All prompts with Barsat's persona
Step 7:  messaging/message_gen.py                  — Anthropic API calls
Step 8:  routers/messaging.py                      — Message gen + approval endpoints
Step 9:  sending/email_sender.py                   — Gmail OAuth + send
Step 10: routers/sending.py + routers/tracking.py  — Send + stats endpoints
Step 11: main.py                                    — Assemble FastAPI app
Step 12: frontend/                                  — React dashboard
Step 13: discovery/linkedin_scraper.py             — LinkedIn (saved for last, highest risk)
Step 14: sending/linkedin_sender.py                — LinkedIn sender
Step 15: scheduler/followup_scheduler.py           — Follow-up automation
```

---

## Testing Notes

- For maps scraper: test with query `"software company Cremorne Melbourne"` — should return 5+ results
- For website parser: test against `https://www.atlassian.com` and a small Melbourne tech co
- For message gen: test with a mock target dict, verify output is under word limits and doesn't contain banned phrases
- For email sender: send a test email to Barsat's own Gmail first before sending to any target
- For LinkedIn: test in non-headless mode, manually verify first connection request before enabling batch

---

## Important Notes for Claude Code

1. **Every file should have proper async/await** — this is an async FastAPI app throughout
2. **All Playwright operations must have try/except** — browser automation fails silently otherwise  
3. **Rate limits are not optional** — they are enforced in code, not just documented
4. **Messages are never auto-sent** — always go through `pending_approval` → user approves → send
5. **LinkedIn credentials never leave the local machine** — never log them, never send to any API
6. **The persona prompts are the most important part** — if messages sound like a template, the whole thing fails
7. **Use `httpx` for async HTTP, not `requests`** — this is an async app
8. **Error responses from FastAPI should be informative** — include what failed and why
9. **Log everything to console with timestamps** — scraping jobs need visibility
10. **The frontend Outreach page is the daily driver** — it needs to be clean and fast
```
