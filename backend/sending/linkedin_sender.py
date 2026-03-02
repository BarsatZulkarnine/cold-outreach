import asyncio
import json
import os
import random
from datetime import datetime, date

from config import (
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    LINKEDIN_HEADLESS,
    LINKEDIN_COOKIES_PATH,
    MAX_CONNECTION_REQUESTS_PER_DAY,
    MAX_DMS_PER_DAY,
    MIN_DELAY_BETWEEN_SENDS_SEC,
    MAX_DELAY_BETWEEN_SENDS_SEC,
)

DAILY_COUNTS_FILE = "linkedin_daily_counts.json"


class LinkedInDailyLimitError(Exception):
    pass


def _load_daily_counts() -> dict:
    if os.path.exists(DAILY_COUNTS_FILE):
        try:
            with open(DAILY_COUNTS_FILE) as f:
                data = json.load(f)
            # Reset if new day
            if data.get("date") != str(date.today()):
                return {"date": str(date.today()), "connection_requests": 0, "dms": 0}
            return data
        except Exception:
            pass
    return {"date": str(date.today()), "connection_requests": 0, "dms": 0}


def _save_daily_counts(data: dict):
    with open(DAILY_COUNTS_FILE, "w") as f:
        json.dump(data, f)


async def _type_slowly(page, selector: str, text: str):
    """Simulate human typing with random delays between keystrokes."""
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def send_linkedin_dm(
    profile_url: str,
    message_body: str,
    message_id: int,
    db,
) -> bool:
    """
    Send a LinkedIn connection request (with note) or DM to an existing connection.
    Updates the message record in DB on success.
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
    except ImportError:
        raise ImportError(
            "Install playwright: pip install playwright playwright-stealth && playwright install chromium"
        )

    from sqlalchemy import select
    from models.schemas import Message, Target

    # Check daily limits
    counts = _load_daily_counts()

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

        # Load cookies
        if os.path.exists(LINKEDIN_COOKIES_PATH):
            try:
                with open(LINKEDIN_COOKIES_PATH) as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
            except Exception:
                pass

        success = False

        try:
            await page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(3, 6))

            # Check for CAPTCHA
            if any(kw in page.url for kw in ["checkpoint", "challenge", "captcha"]):
                print("[LinkedIn Sender] ⚠️  CAPTCHA detected. Manual intervention needed.")
                print("[LinkedIn Sender] Waiting 120s for you to solve it...")
                await asyncio.sleep(120)

            # Check for rate limiting (429 page)
            if "429" in page.url or "too-many-requests" in page.url.lower():
                print("[LinkedIn Sender] ⚠️  Rate limited by LinkedIn!")
                await browser.close()
                return False

            # Try to find "Message" button first (already connected)
            message_btn = await page.query_selector('button:has-text("Message")')
            if message_btn:
                if counts["dms"] >= MAX_DMS_PER_DAY:
                    raise LinkedInDailyLimitError(f"Daily DM limit reached ({MAX_DMS_PER_DAY})")

                print(f"[LinkedIn Sender] Sending DM to {profile_url}")
                await message_btn.click()
                await asyncio.sleep(2)

                # Type message
                msg_input = await page.query_selector('[role="textbox"]')
                if msg_input:
                    await msg_input.click()
                    for char in message_body:
                        await page.keyboard.type(char)
                        await asyncio.sleep(random.uniform(0.04, 0.12))
                    await asyncio.sleep(1)

                    # Send
                    send_btn = await page.query_selector('button[type="submit"]')
                    if send_btn:
                        await send_btn.click()
                        await asyncio.sleep(2)
                        counts["dms"] += 1
                        _save_daily_counts(counts)
                        success = True
                        print("[LinkedIn Sender] DM sent ✓")

            else:
                # Try "Connect" button
                connect_btn = await page.query_selector('button:has-text("Connect")')
                if not connect_btn:
                    print(f"[LinkedIn Sender] No Connect or Message button found at {profile_url}. Skipping.")
                    await browser.close()
                    return False

                if counts["connection_requests"] >= MAX_CONNECTION_REQUESTS_PER_DAY:
                    raise LinkedInDailyLimitError(
                        f"Daily connection request limit reached ({MAX_CONNECTION_REQUESTS_PER_DAY})"
                    )

                print(f"[LinkedIn Sender] Sending connection request to {profile_url}")
                await connect_btn.click()
                await asyncio.sleep(2)

                # Click "Add a note"
                add_note_btn = await page.query_selector('button:has-text("Add a note")')
                if add_note_btn:
                    await add_note_btn.click()
                    await asyncio.sleep(1)

                    note_text = message_body[:200]  # LinkedIn limits connection notes to 200 chars
                    note_input = await page.query_selector('textarea[name="message"]')
                    if note_input:
                        await note_input.click()
                        for char in note_text:
                            await page.keyboard.type(char)
                            await asyncio.sleep(random.uniform(0.04, 0.12))
                        await asyncio.sleep(1)

                # Send connection request
                send_btn = await page.query_selector('button:has-text("Send")')
                if send_btn:
                    await send_btn.click()
                    await asyncio.sleep(2)
                    counts["connection_requests"] += 1
                    _save_daily_counts(counts)
                    success = True
                    print("[LinkedIn Sender] Connection request sent ✓")

        except LinkedInDailyLimitError:
            raise
        except Exception as e:
            print(f"[LinkedIn Sender] Error: {e}")
            success = False
        finally:
            # Save updated cookies
            try:
                cookies = await context.cookies()
                with open(LINKEDIN_COOKIES_PATH, "w") as f:
                    json.dump(cookies, f)
            except Exception:
                pass
            await browser.close()

    if success:
        # Update DB
        result = await db.execute(select(Message).where(Message.id == message_id))
        msg = result.scalar_one_or_none()
        if msg:
            msg.sent_at = datetime.utcnow()
            msg.status = "sent"
            target_result = await db.execute(select(Target).where(Target.id == msg.target_id))
            target = target_result.scalar_one_or_none()
            if target and target.status in ("discovered", "message_generated", "approved"):
                target.status = "sent"
                target.updated_at = datetime.utcnow()
            await db.commit()

        # Delay before next send
        delay = random.uniform(MIN_DELAY_BETWEEN_SENDS_SEC, MAX_DELAY_BETWEEN_SENDS_SEC)
        print(f"[LinkedIn Sender] Waiting {delay:.0f}s before next action.")
        await asyncio.sleep(delay)

    return success
