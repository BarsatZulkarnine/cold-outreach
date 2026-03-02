import asyncio
import re
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

# Email patterns that are useful vs noise
PRIORITY_EMAIL_PATTERNS = re.compile(
    r"(cto|tech|engineering|dev|hi|hello|info|contact|careers|jobs)@",
    re.IGNORECASE,
)
SKIP_EMAIL_PATTERNS = re.compile(
    r"(noreply|no-reply|support|privacy|legal|abuse|spam|unsubscribe)@",
    re.IGNORECASE,
)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}")

# File extensions that appear in image/asset filenames — not real email TLDs
_ASSET_EXTENSIONS = {
    'webp', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', 'bmp', 'tiff',
    'pdf', 'zip', 'css', 'js', 'woff', 'woff2', 'ttf', 'eot', 'mp4',
    'mp3', 'mov', 'wasm', 'map', 'xml', 'php',
}

def _is_real_email(email: str) -> bool:
    """Filter out image filenames and asset paths incorrectly matched as emails."""
    if '@' not in email:
        return False
    local, domain = email.rsplit('@', 1)
    tld = domain.rsplit('.', 1)[-1].lower()
    if tld in _ASSET_EXTENSIONS:
        return False
    # Local part with a date pattern = filename, not email
    if re.search(r'\d{4}-\d{2}-\d{2}', local):
        return False
    # Domain must have at least one dot and no slashes
    if '.' not in domain or '/' in domain:
        return False
    return True

# Contact titles to look for
RELEVANT_TITLES = [
    "CTO", "CEO", "Head of Engineering", "Tech Lead", "Technical Lead",
    "Software Engineer", "Engineering Manager", "VP Engineering",
    "VP of Engineering", "Director of Engineering", "Lead Developer",
    "Principal Engineer", "Senior Engineer",
]

# Career page paths to probe
CAREER_PATHS = ["/careers", "/jobs", "/work-with-us", "/join-us", "/hiring", "/join", "/team/careers"]

# Keywords that suggest junior/grad-friendly roles
JUNIOR_KEYWORDS = re.compile(
    r"\b(junior|grad(uate)?|entry[\s-]level|new grad|internship|intern|associate)\b",
    re.IGNORECASE,
)

# Tech stack detection patterns (script src, meta, footer text)
TECH_PATTERNS = {
    "React": re.compile(r"react(\.min)?\.js|react-dom", re.IGNORECASE),
    "Vue.js": re.compile(r"vue(\.min)?\.js|vue-router", re.IGNORECASE),
    "Angular": re.compile(r"angular(\.min)?\.js|@angular", re.IGNORECASE),
    "Next.js": re.compile(r"/_next/|next\.js", re.IGNORECASE),
    "Nuxt.js": re.compile(r"/_nuxt/|nuxt\.js", re.IGNORECASE),
    "Django": re.compile(r"django|csrfmiddlewaretoken", re.IGNORECASE),
    "Ruby on Rails": re.compile(r"rails|ruby-on-rails|authenticity_token", re.IGNORECASE),
    "Laravel": re.compile(r"laravel|blade\.php", re.IGNORECASE),
    "WordPress": re.compile(r"wp-content|wp-includes|wordpress", re.IGNORECASE),
    "AWS": re.compile(r"amazonaws\.com|cloudfront\.net|s3\.amazonaws", re.IGNORECASE),
    "Heroku": re.compile(r"heroku", re.IGNORECASE),
    "Vercel": re.compile(r"vercel\.app|\.vercel\.com", re.IGNORECASE),
    "Shopify": re.compile(r"shopify|myshopify\.com", re.IGNORECASE),
    "HubSpot": re.compile(r"hubspot|hs-scripts", re.IGNORECASE),
}


def _extract_emails(text: str) -> list[str]:
    found = EMAIL_REGEX.findall(text)
    cleaned = []
    for email in found:
        email = email.lower().strip(".,;")
        if not _is_real_email(email):
            continue
        if SKIP_EMAIL_PATTERNS.search(email):
            continue
        if email not in cleaned:
            cleaned.append(email)

    # Sort so priority emails come first
    priority = [e for e in cleaned if PRIORITY_EMAIL_PATTERNS.search(e)]
    rest = [e for e in cleaned if e not in priority]
    return priority + rest


def _detect_tech(html: str) -> list[str]:
    detected = []
    for tech, pattern in TECH_PATTERNS.items():
        if pattern.search(html):
            detected.append(tech)
    return detected


def _extract_contacts(soup: BeautifulSoup) -> list[dict]:
    contacts = []
    text_blocks = soup.get_text(separator=" ")

    for title in RELEVANT_TITLES:
        pattern = re.compile(
            rf"([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*[,\-–|]\s*{re.escape(title)}",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text_blocks):
            name = match.group(1).strip()
            if name and len(name.split()) >= 2:
                contacts.append({"name": name, "title": title})

    # Deduplicate by name
    seen = set()
    unique = []
    for c in contacts:
        if c["name"] not in seen:
            seen.add(c["name"])
            unique.append(c)

    return unique[:5]  # top 5


async def _fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        resp = await client.get(url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


async def parse_website(url: str) -> dict:
    """
    Given a company website URL, extract:
    - emails
    - contacts (name + title)
    - has_open_roles / open_role_url
    - tech_hints (detected stack)
    - raw_notes
    """
    if not url:
        return {
            "emails": [], "contacts": [], "has_open_roles": False,
            "open_role_url": None, "tech_hints": [], "raw_notes": "",
        }

    # Normalize URL
    if not url.startswith("http"):
        url = "https://" + url

    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    emails: list[str] = []
    contacts: list[dict] = []
    tech_hints: list[str] = []
    has_open_roles = False
    open_role_url = None
    notes_parts: list[str] = []

    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(headers=headers) as client:
        # 1. Fetch homepage
        homepage_html = await _fetch(client, url)
        if homepage_html:
            emails += _extract_emails(homepage_html)
            tech_hints += _detect_tech(homepage_html)

        # 2. Probe key subpages
        subpages = ["/contact", "/about", "/team", "/about-us"]
        for path in subpages:
            html = await _fetch(client, base + path)
            if html:
                emails += _extract_emails(html)
                soup = BeautifulSoup(html, "html.parser")
                contacts += _extract_contacts(soup)
                await asyncio.sleep(0.3)

        # 3. Check careers page
        for path in CAREER_PATHS:
            html = await _fetch(client, base + path)
            if html:
                open_role_url = base + path
                lower_html = html.lower()
                has_open_roles = bool(JUNIOR_KEYWORDS.search(lower_html))
                emails += _extract_emails(html)
                notes_parts.append(f"Careers page found: {open_role_url} | Junior roles: {has_open_roles}")
                await asyncio.sleep(0.3)
                break  # stop at first found

    # Deduplicate
    emails = list(dict.fromkeys(emails))[:5]
    tech_hints = list(dict.fromkeys(tech_hints))

    # Deduplicate contacts by name
    seen_names = set()
    unique_contacts = []
    for c in contacts:
        if c["name"] not in seen_names:
            seen_names.add(c["name"])
            unique_contacts.append(c)

    raw_notes = " | ".join(notes_parts) if notes_parts else ""

    return {
        "emails": emails,
        "contacts": unique_contacts[:3],
        "has_open_roles": has_open_roles,
        "open_role_url": open_role_url,
        "tech_hints": tech_hints,
        "raw_notes": raw_notes,
    }
