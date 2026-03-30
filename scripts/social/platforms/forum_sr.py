"""
Serbian Forum Automation — Playwright-based headless browser poster.

Supported forums:
  - realx3mforum.com  (vBulletin)
  - forum.benchmark.rs (phpBB)
  - forum.krstarica.com (phpBB variant)

Anti-detection features:
  - Randomised typing delays (human-like)
  - Randomised pre-action pauses
  - Session persistence (cookies saved to disk)
  - User-agent rotation pool
"""

import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Forum configs
# ---------------------------------------------------------------------------

FORUM_CONFIGS = {
    "realx3m": {
        "base_url": "https://realx3mforum.com",
        "engine": "vbulletin",
        "login_url": "https://realx3mforum.com/login.php",
        "login_username_selector": 'input[name="vb_login_username"]',
        "login_password_selector": 'input[name="vb_login_password"]',
        "login_submit_selector": 'input[type="submit"][value*="Log in"], input[type="submit"][value*="Prijava"]',
        "reply_box_selector": 'textarea[name="message"]',
        "reply_submit_selector": 'input[type="submit"][name="sbutton"]',
        "new_post_subject_selector": 'input[name="subject"]',
    },
    "benchmark_rs": {
        "base_url": "https://forum.benchmark.rs",
        "engine": "phpbb",
        "login_url": "https://forum.benchmark.rs/ucp.php?mode=login",
        "login_username_selector": 'input[name="username"]',
        "login_password_selector": 'input[name="password"]',
        "login_submit_selector": 'input[type="submit"][name="login"]',
        "reply_box_selector": 'textarea[name="message"]',
        "reply_submit_selector": 'input[name="post"]',
        "new_post_subject_selector": 'input[name="subject"]',
    },
    "krstarica": {
        "base_url": "https://forum.krstarica.com",
        "engine": "phpbb",
        "login_url": "https://forum.krstarica.com/ucp.php?mode=login",
        "login_username_selector": 'input[name="username"]',
        "login_password_selector": 'input[name="password"]',
        "login_submit_selector": 'input[type="submit"][name="login"]',
        "reply_box_selector": 'textarea[name="message"]',
        "reply_submit_selector": 'input[name="post"]',
        "new_post_subject_selector": 'input[name="subject"]',
    },
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


@dataclass
class PostResult:
    success: bool
    post_id: str
    url: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Human-like typing helper
# ---------------------------------------------------------------------------

async def human_type(page: Page, selector: str, text: str):
    """Type text character-by-character with randomised delays."""
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.3, 0.7))
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.04, 0.18))
    await asyncio.sleep(random.uniform(0.2, 0.5))


async def human_pause(min_sec: float = 0.8, max_sec: float = 2.5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))


# ---------------------------------------------------------------------------
# ForumPoster class
# ---------------------------------------------------------------------------

class ForumPoster:
    def __init__(self, forum_key: str, credentials: dict, session_dir: Path, dry_run: bool = False):
        """
        Args:
            forum_key: one of 'realx3m', 'benchmark_rs', 'krstarica'
            credentials: {'username': ..., 'password': ...}
            session_dir: path to store cookies/session state
            dry_run: if True, navigate and log but do not submit
        """
        if forum_key not in FORUM_CONFIGS:
            raise ValueError(f"Unknown forum: {forum_key}. Valid: {list(FORUM_CONFIGS)}")
        self.config = FORUM_CONFIGS[forum_key]
        self.forum_key = forum_key
        self.credentials = credentials
        self.session_file = session_dir / f"{forum_key}_session.json"
        self.dry_run = dry_run
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        storage_state = str(self.session_file) if self.session_file.exists() else None
        self._context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            storage_state=storage_state,
            locale="sr-RS",
            timezone_id="Europe/Belgrade",
        )
        return self

    async def __aexit__(self, *args):
        if self._context:
            await self._context.storage_state(path=str(self.session_file))
            await self._context.close()
        if self._browser:
            await self._browser.close()
        await self._pw.stop()

    async def _new_page(self) -> Page:
        page = await self._context.new_page()
        # Hide automation signals
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        return page

    async def _is_logged_in(self, page: Page) -> bool:
        """Check if current session is authenticated."""
        await page.goto(self.config["base_url"], wait_until="domcontentloaded")
        await human_pause(0.5, 1.0)
        content = await page.content()
        # Generic check: logged-in pages usually show username or logout link
        indicators = ["logout", "odjavite", "odjava", "log out", self.credentials.get("username", "").lower()]
        return any(ind.lower() in content.lower() for ind in indicators)

    async def login(self) -> bool:
        """Log in to the forum. Returns True on success."""
        page = await self._new_page()
        try:
            if await self._is_logged_in(page):
                logger.info("[%s] Already logged in (session cookie valid)", self.forum_key)
                await page.close()
                return True

            logger.info("[%s] Logging in as %s", self.forum_key, self.credentials["username"])
            await page.goto(self.config["login_url"], wait_until="domcontentloaded")
            await human_pause()

            await human_type(page, self.config["login_username_selector"], self.credentials["username"])
            await human_type(page, self.config["login_password_selector"], self.credentials["password"])
            await human_pause(0.5, 1.2)

            await page.click(self.config["login_submit_selector"])
            await page.wait_for_load_state("domcontentloaded")
            await human_pause(1.0, 2.0)

            # Verify
            success = await self._is_logged_in(page)
            if success:
                logger.info("[%s] Login successful", self.forum_key)
            else:
                logger.error("[%s] Login failed — check credentials", self.forum_key)
            await page.close()
            return success
        except Exception as exc:
            logger.exception("[%s] Login error: %s", self.forum_key, exc)
            await page.close()
            return False

    async def reply_to_thread(self, thread_url: str, body: str, post_id: str) -> PostResult:
        """Post a reply to an existing thread."""
        page = await self._new_page()
        try:
            logger.info("[%s] Navigating to thread: %s", self.forum_key, thread_url)
            await page.goto(thread_url, wait_until="domcontentloaded")
            await human_pause(1.5, 3.0)

            # Find the reply / quick-reply box
            reply_sel = self.config["reply_box_selector"]
            # Try quick-reply first; fall back to clicking Reply button
            try:
                await page.wait_for_selector(reply_sel, timeout=5000)
            except Exception:
                # Try clicking a "Reply" button to reveal the form
                for btn_text in ["Reply", "Odgovori", "Odgovor", "Brzi odgovor"]:
                    btn = page.get_by_text(btn_text, exact=False)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await human_pause(1.0, 2.0)
                        break

            await human_type(page, reply_sel, body)
            await human_pause(1.5, 3.0)

            if self.dry_run:
                logger.info("[DRY RUN] Would submit reply to %s", thread_url)
                await page.close()
                return PostResult(success=True, post_id=post_id, url=thread_url)

            await page.click(self.config["reply_submit_selector"])
            await page.wait_for_load_state("domcontentloaded")
            await human_pause(1.0, 2.0)

            final_url = page.url
            logger.info("[%s] Reply posted: %s", self.forum_key, final_url)
            await page.close()
            return PostResult(success=True, post_id=post_id, url=final_url)

        except Exception as exc:
            logger.exception("[%s] Reply error: %s", self.forum_key, exc)
            await page.close()
            return PostResult(success=False, post_id=post_id, error=str(exc))

    async def new_post(self, forum_section_url: str, subject: str, body: str, post_id: str) -> PostResult:
        """Create a new thread in a forum section."""
        page = await self._new_page()
        try:
            logger.info("[%s] Creating new post in section: %s", self.forum_key, forum_section_url)
            await page.goto(forum_section_url, wait_until="domcontentloaded")
            await human_pause(1.5, 3.0)

            # Click "New Thread" / "Nova tema" button
            for btn_text in ["New Thread", "Nova tema", "Post New Thread", "Novi post", "Novi temu"]:
                btn = page.get_by_text(btn_text, exact=False)
                if await btn.count() > 0:
                    await btn.first.click()
                    await human_pause(1.5, 2.5)
                    break

            await human_type(page, self.config["new_post_subject_selector"], subject)
            await human_type(page, self.config["reply_box_selector"], body)
            await human_pause(2.0, 4.0)

            if self.dry_run:
                logger.info("[DRY RUN] Would submit new post '%s'", subject)
                await page.close()
                return PostResult(success=True, post_id=post_id, url=forum_section_url)

            await page.click(self.config["reply_submit_selector"])
            await page.wait_for_load_state("domcontentloaded")
            await human_pause(1.5, 3.0)

            final_url = page.url
            logger.info("[%s] New post created: %s", self.forum_key, final_url)
            await page.close()
            return PostResult(success=True, post_id=post_id, url=final_url)

        except Exception as exc:
            logger.exception("[%s] New post error: %s", self.forum_key, exc)
            await page.close()
            return PostResult(success=False, post_id=post_id, error=str(exc))


# ---------------------------------------------------------------------------
# Convenience runner
# ---------------------------------------------------------------------------

async def post_to_forum(
    forum_key: str,
    credentials: dict,
    post: dict,
    thread_url: Optional[str],
    section_url: Optional[str],
    session_dir: Path,
    dry_run: bool = False,
) -> PostResult:
    """
    High-level helper called by the main poster CLI.

    Args:
        forum_key: 'realx3m' | 'benchmark_rs' | 'krstarica'
        credentials: {'username': ..., 'password': ...}
        post: dict from forum_posts.json
        thread_url: URL to reply to (for type='reply')
        section_url: URL of forum section (for type='new_post')
        session_dir: directory to persist session cookies
        dry_run: simulate without submitting
    """
    session_dir.mkdir(parents=True, exist_ok=True)
    async with ForumPoster(forum_key, credentials, session_dir, dry_run=dry_run) as poster:
        if not await poster.login():
            return PostResult(success=False, post_id=post["id"], error="Login failed")

        if post["type"] == "reply":
            if not thread_url:
                return PostResult(success=False, post_id=post["id"], error="thread_url required for reply type")
            return await poster.reply_to_thread(thread_url, post["body"], post["id"])
        elif post["type"] == "new_post":
            if not section_url:
                return PostResult(success=False, post_id=post["id"], error="section_url required for new_post type")
            return await poster.new_post(section_url, post.get("subject", ""), post["body"], post["id"])
        else:
            return PostResult(success=False, post_id=post["id"], error=f"Unknown post type: {post['type']}")
