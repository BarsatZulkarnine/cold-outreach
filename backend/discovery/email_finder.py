import asyncio
import smtplib
import socket
import dns.resolver
import httpx
from config import HUNTER_API_KEY

HUNTER_BASE = "https://api.hunter.io/v2"

PATTERNS = [
    "{first}.{last}@{domain}",
    "{first}@{domain}",
    "{first}{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}.{l}@{domain}",
    "{first}_{last}@{domain}",
]


def _build_candidates(first: str, last: str, domain: str) -> list[str]:
    first = first.lower().strip()
    last = last.lower().strip()
    f = first[0] if first else ""
    l = last[0] if last else ""
    candidates = []
    for pattern in PATTERNS:
        candidate = pattern.format(
            first=first, last=last, domain=domain, f=f, l=l
        )
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _get_mx_host(domain: str) -> str | None:
    try:
        records = dns.resolver.resolve(domain, "MX")
        mx = sorted(records, key=lambda r: r.preference)[0]
        return str(mx.exchange).rstrip(".")
    except Exception:
        return None


def _smtp_verify(email: str, mx_host: str) -> bool:
    """
    Lightweight SMTP RCPT TO check.
    Returns True if the server doesn't explicitly reject the address.
    Many servers will accept anything (catch-all), so treat True as "maybe valid".
    """
    try:
        with smtplib.SMTP(timeout=8) as smtp:
            smtp.connect(mx_host, 25)
            smtp.ehlo("outreach-verify.local")
            smtp.mail("verify@outreach-verify.local")
            code, _ = smtp.rcpt(email)
            return code not in (550, 551, 553, 554)
    except (smtplib.SMTPException, socket.error, OSError):
        # Connection blocked, timeout, or server refused — treat as unknown
        return False


async def hunter_find(first_name: str, last_name: str, domain: str) -> str | None:
    """Strategy A: Hunter.io email finder API."""
    if not HUNTER_API_KEY:
        return None

    params = {
        "first_name": first_name,
        "last_name": last_name,
        "domain": domain,
        "api_key": HUNTER_API_KEY,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{HUNTER_BASE}/email-finder", params=params, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                email = data.get("email")
                confidence = data.get("score", 0)
                if email and confidence >= 70:
                    print(f"[EmailFinder] Hunter found: {email} (confidence: {confidence})")
                    return email
    except Exception as e:
        print(f"[EmailFinder] Hunter.io error: {e}")

    return None


async def guess_email(first_name: str, last_name: str, domain: str) -> str | None:
    """Strategy B: Pattern guessing + SMTP verification."""
    candidates = _build_candidates(first_name, last_name, domain)
    mx_host = _get_mx_host(domain)

    if not mx_host:
        print(f"[EmailFinder] Could not resolve MX for {domain}")
        # Still return best-guess pattern even without SMTP verification
        return candidates[0] if candidates else None

    print(f"[EmailFinder] MX for {domain}: {mx_host}")

    for candidate in candidates:
        try:
            valid = await asyncio.get_event_loop().run_in_executor(
                None, _smtp_verify, candidate, mx_host
            )
            if valid:
                print(f"[EmailFinder] SMTP accepted: {candidate}")
                return candidate
        except Exception:
            continue
        await asyncio.sleep(0.2)

    return None


async def find_email(first_name: str, last_name: str, domain: str) -> str | None:
    """
    Try Hunter.io first, fall back to SMTP pattern guessing.
    Returns best-guess email or None.
    """
    if not first_name or not last_name or not domain:
        return None

    # Strategy A
    email = await hunter_find(first_name, last_name, domain)
    if email:
        return email

    # Strategy B
    email = await guess_email(first_name, last_name, domain)
    if email:
        return email

    print(f"[EmailFinder] No email found for {first_name} {last_name} @ {domain}")
    return None
