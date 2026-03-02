import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from config import (
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    LINKEDIN_HEADLESS,
    LINKEDIN_COOKIES_PATH,
    MAX_PROFILES_PER_SESSION,
    MAX_SEARCHES_PER_DAY,
    MIN_DELAY_BETWEEN_ACTIONS_SEC,
    MAX_DELAY_BETWEEN_ACTIONS_SEC,
)

RATE_LIMIT_FILE = "linkedin_rate_limit.json"


class RateLimitError(Exception):
    pass


def _load_rate_limit() -> dict:
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"searches_today": 0, "date": str(datetime.utcnow().date()), "last_run": None, "blocked_until": None}


def _save_rate_limit(data: dict):
    with open(RATE_LIMIT_FILE, "w") as f:
        json.dump(data, f)


def _check_rate_limits():
    data = _load_rate_limit()

    # Check if blocked
    if data.get("blocked_until"):
        blocked_until = datetime.fromisoformat(data["blocked_until"])
        if datetime.utcnow() < blocked_until:
            raise RateLimitError(
                f"LinkedIn is blocked until {blocked_until.isoformat()}. "
                "Rate-limited by LinkedIn — wait 24h."
            )
        else:
            data["blocked_until"] = None

    # Reset daily count if new day
    if data.get("date") != str(datetime.utcnow().date()):
        data["searches_today"] = 0
        data["date"] = str(datetime.utcnow().date())

    # Check 2-hour cooldown between runs
    if data.get("last_run"):
        last_run = datetime.fromisoformat(data["last_run"])
        if datetime.utcnow() - last_run < timedelta(hours=2):
            mins_remaining = int((timedelta(hours=2) - (datetime.utcnow() - last_run)).total_seconds() / 60)
            raise RateLimitError(
                f"LinkedIn scraper ran recently. Wait {mins_remaining} more minutes."
            )

    if data["searches_today"] >= MAX_SEARCHES_PER_DAY:
        raise RateLimitError(
            f"Daily LinkedIn search limit reached ({MAX_SEARCHES_PER_DAY}). Try again tomorrow."
        )

    return data


async def _random_delay():
    delay = random.uniform(MIN_DELAY_BETWEEN_ACTIONS_SEC, MAX_DELAY_BETWEEN_ACTIONS_SEC)
    print(f"[LinkedIn] Waiting {delay:.0f}s before next action...")
    await asyncio.sleep(delay)


async def search_linkedin_contacts(
    search_query: str,
    location: str = "Melbourne, Victoria, Australia",
    max_results: int = 15,
) -> list[dict]:
    """
    Search LinkedIn for engineering contacts at Melbourne companies.

    IMPORTANT: LinkedIn blocks bots aggressively.
    - Runs in non-headless mode so you can solve CAPTCHAs manually
    - Stores cookies after first login for reuse
    - Hard limits: MAX_PROFILES_PER_SESSION=5, MAX_SEARCHES_PER_DAY=3
    - 3-7 minute delays between profile visits
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
    except ImportError:
        raise ImportError(
            "Install playwright and playwright-stealth: "
            "pip install playwright playwright-stealth && playwright install chromium"
        )

    # Check rate limits before starting
    rate_data = _check_rate_limits()

    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env")

    results: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=LINKEDIN_HEADLESS)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()

        # Load saved cookies if available
        if os.path.exists(LINKEDIN_COOKIES_PATH):
            try:
                with open(LINKEDIN_COOKIES_PATH) as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                print("[LinkedIn] Loaded saved cookies.")
            except Exception:
                pass

        # Navigate to LinkedIn
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Check if we need to log in
        # Must check path specifically — redirect URLs like /login?session_redirect=%2Ffeed%2F
        # contain "feed" in the query string and would falsely pass a naive check
        from urllib.parse import urlparse
        parsed_url = urlparse(page.url)
        if "/feed" not in parsed_url.path:
            print("[LinkedIn] Not logged in.")
            print("[LinkedIn] ⚠️  Please log in manually in the browser window.")
            print("[LinkedIn] Waiting up to 90 seconds for you to log in...")

            # Wait until we land on the feed (user logs in manually)
            try:
                await page.wait_for_url("https://www.linkedin.com/feed/**", timeout=90_000)
                print("[LinkedIn] Login detected. Continuing...")
            except Exception:
                print("[LinkedIn] Timed out waiting for login. Trying to continue anyway...")

            # Save cookies after login
            cookies = await context.cookies()
            with open(LINKEDIN_COOKIES_PATH, "w") as f:
                json.dump(cookies, f)
            print("[LinkedIn] Cookies saved.")

        # Check for CAPTCHA or security challenge
        if any(kw in page.url for kw in ["checkpoint", "challenge", "captcha"]):
            print("[LinkedIn] ⚠️  Security challenge detected. Please solve it manually in the browser window.")
            print("[LinkedIn] Waiting 120 seconds for manual intervention...")
            await asyncio.sleep(120)

        # Search for people — include location in keywords (avoids unreliable geoUrn IDs)
        keywords = f"{search_query} Melbourne Australia".replace(" ", "%20")
        search_url = (
            "https://www.linkedin.com/search/results/people/"
            f"?keywords={keywords}&origin=GLOBAL_SEARCH_HEADER"
        )

        print(f"[LinkedIn] Searching: {search_query!r}")
        await page.goto(search_url, wait_until="domcontentloaded")
        # LinkedIn is a SPA — wait longer for dynamic content to render
        await asyncio.sleep(random.uniform(5, 8))

        # Scroll down to trigger lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(2)

        # Extract search results — handle both absolute and relative /in/ URLs
        profile_links = []
        try:
            cards = await page.query_selector_all('a[href*="/in/"]')
            for card in cards:
                href = await card.get_attribute("href")
                if not href or "/in/" not in href:
                    continue
                # Normalise to absolute URL
                if href.startswith("/"):
                    href = "https://www.linkedin.com" + href
                # Skip non-profile links (e.g. /in/feed, company pages)
                if "/in/" not in href:
                    continue
                clean = href.split("?")[0].rstrip("/")
                if clean not in profile_links:
                    profile_links.append(clean)
                if len(profile_links) >= max_results:
                    break
        except Exception as e:
            print(f"[LinkedIn] Error extracting links: {e}")

        print(f"[LinkedIn] Current URL: {page.url}")

        print(f"[LinkedIn] Found {len(profile_links)} profile links")

        # Visit individual profiles (capped at MAX_PROFILES_PER_SESSION)
        profiles_to_visit = profile_links[:MAX_PROFILES_PER_SESSION]

        for i, profile_url in enumerate(profiles_to_visit):
            print(f"[LinkedIn] Visiting profile {i+1}/{len(profiles_to_visit)}: {profile_url}")

            try:
                await page.goto(profile_url, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(3, 7))

                # Check for rate limit page
                if "429" in page.url or "too-many-requests" in page.url.lower():
                    print("[LinkedIn] ⚠️  Rate limited! Blocking LinkedIn for 24 hours.")
                    rate_data["blocked_until"] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
                    _save_rate_limit(rate_data)
                    break

                # Extract profile data
                name = ""
                title = ""
                company = ""
                about = ""

                try:
                    name_el = await page.query_selector("h1")
                    if name_el:
                        name = (await name_el.inner_text()).strip()
                except Exception:
                    pass

                try:
                    title_el = await page.query_selector(".text-body-medium")
                    if title_el:
                        title = (await title_el.inner_text()).strip()
                except Exception:
                    pass

                try:
                    # Current company from experience section
                    company_els = await page.query_selector_all('[aria-label="Current company"]')
                    if company_els:
                        company = (await company_els[0].inner_text()).strip()
                except Exception:
                    pass

                try:
                    about_el = await page.query_selector("#about ~ div .visually-hidden")
                    if about_el:
                        about = (await about_el.inner_text()).strip()[:500]
                except Exception:
                    pass

                if name:
                    results.append({
                        "source": "linkedin",
                        "company_name": company or "Unknown",
                        "company_website": None,
                        "contact_name": name,
                        "contact_title": title,
                        "linkedin_url": profile_url,
                        "notes": about[:300] if about else None,
                        "status": "discovered",
                    })
                    print(f"[LinkedIn]   ✓ {name} — {title} @ {company}")

            except Exception as e:
                print(f"[LinkedIn] Error visiting {profile_url}: {e}")

            # Long delay between profile visits
            if i < len(profiles_to_visit) - 1:
                await _random_delay()

        # Save updated cookies
        try:
            cookies = await context.cookies()
            with open(LINKEDIN_COOKIES_PATH, "w") as f:
                json.dump(cookies, f)
        except Exception:
            pass

        await browser.close()

    # Update rate limit tracking
    rate_data["searches_today"] = rate_data.get("searches_today", 0) + 1
    rate_data["last_run"] = datetime.utcnow().isoformat()
    _save_rate_limit(rate_data)

    print(f"[LinkedIn] Done. Extracted {len(results)} profiles.")
    return results
