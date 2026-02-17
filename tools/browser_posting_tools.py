"""Indeed Browser Posting Tools — posts jobs directly on Indeed via headless Playwright.

No API key required. Uses employer email + password stored as env vars:
  INDEED_EMAIL     — employer account email
  INDEED_PASSWORD  — employer account password

The job is posted to Indeed Thailand (th.indeed.com) using a headless
Chromium browser that simulates the employer portal flow.

Requires Playwright + Chromium (installed via Dockerfile).
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Optional

from agno.tools import Toolkit

# Stealth JS injected into every page to remove automation fingerprints
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
"""


class IndeedBrowserPosterTools(Toolkit):
    """Post jobs to Indeed employer portal using headless browser automation."""

    def __init__(self, email: str = "", password: str = ""):
        super().__init__(name="indeed_browser_poster")
        self.email = email or os.getenv("INDEED_EMAIL", "")
        self.password = password or os.getenv("INDEED_PASSWORD", "")
        self.register(self.post_job_to_indeed)
        self.register(self.check_indeed_login)

    # ------------------------------------------------------------------
    # Public tools
    # ------------------------------------------------------------------

    def check_indeed_login(self) -> str:
        """Check if Indeed credentials are configured and login works.

        Returns:
            JSON with login status and any debug info.
        """
        if not self.email or not self.password:
            return json.dumps({
                "success": False,
                "error": "INDEED_EMAIL or INDEED_PASSWORD env var not set.",
            })
        return asyncio.run(self._check_login_async())

    def post_job_to_indeed(
        self,
        title: str,
        description: str,
        location: str,
        apply_email: str,
        company: str = "",
        job_type: str = "FULL_TIME",
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
    ) -> str:
        """Post a job directly to Indeed Thailand using browser automation.

        Args:
            title: Job title (e.g. "Padel Coach")
            description: Full job description — plain text, 200-5000 chars.
            location: Location string (e.g. "Bangkok, Thailand")
            apply_email: Email address where candidates apply
            company: Company name (auto-filled from Indeed account)
            job_type: FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP
            salary_min: Minimum monthly salary in THB (optional)
            salary_max: Maximum monthly salary in THB (optional)

        Returns:
            JSON with success status and job URL or error details.
        """
        if not self.email or not self.password:
            return json.dumps({
                "success": False,
                "error": "INDEED_EMAIL and INDEED_PASSWORD must be set in Railway env vars.",
            })

        return asyncio.run(self._post_job_async(
            title, description, location, apply_email, company, job_type, salary_min, salary_max,
        ))

    # ------------------------------------------------------------------
    # Async implementation
    # ------------------------------------------------------------------

    async def _new_stealth_context(self, playwright):
        """Launch Chromium with anti-bot stealth settings."""
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,800",
                "--disable-infobars",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Asia/Bangkok",
            java_script_enabled=True,
        )
        await context.add_init_script(_STEALTH_JS)
        return browser, context

    async def _check_login_async(self) -> str:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return json.dumps({"success": False, "error": "playwright not installed"})

        async with async_playwright() as p:
            browser, context = await self._new_stealth_context(p)
            page = await context.new_page()
            try:
                result = await _indeed_login(page, self.email, self.password)
                return json.dumps({"success": True, "message": "Login successful.", "url": page.url})
            except Exception as e:
                screenshot_b64 = await _screenshot_b64(page)
                return json.dumps({
                    "success": False,
                    "error": str(e),
                    "page_url": page.url,
                    "page_title": await page.title(),
                    "debug_screenshot_b64": screenshot_b64[:200] + "..." if screenshot_b64 else None,
                })
            finally:
                await browser.close()

    async def _post_job_async(
        self,
        title: str,
        description: str,
        location: str,
        apply_email: str,
        company: str,
        job_type: str,
        salary_min: Optional[int],
        salary_max: Optional[int],
    ) -> str:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return json.dumps({
                "success": False,
                "error": "playwright not installed — rebuild the container",
            })

        async with async_playwright() as p:
            browser, context = await self._new_stealth_context(p)
            page = await context.new_page()
            try:
                # Step 1: Login
                await _indeed_login(page, self.email, self.password)

                # Step 2: Navigate to post job
                await page.goto(
                    "https://employers.indeed.com/jobs/post",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
                await page.wait_for_timeout(2000)

                # Step 3: Job Title
                title_input = await _wait_for_any(page, [
                    'input[name="jobTitle"]',
                    'input[id="jobTitle"]',
                    'input[placeholder*="title" i]',
                    'input[aria-label*="title" i]',
                    'input[type="text"]',
                ], timeout=15000)
                if not title_input:
                    page_info = f"URL: {page.url} | Title: {await page.title()}"
                    raise Exception(f"Job title input not found. Page: {page_info}")
                await title_input.fill(title)
                await _click_continue(page)
                await page.wait_for_timeout(1500)

                # Step 4: Location
                try:
                    loc_input = await _wait_for_any(page, [
                        'input[name="location"]',
                        'input[id="location"]',
                        'input[placeholder*="location" i]',
                        'input[aria-label*="location" i]',
                    ], timeout=6000)
                    if loc_input:
                        await loc_input.triple_click()
                        await loc_input.fill(location)
                        await page.wait_for_timeout(1000)
                        await page.keyboard.press("Escape")
                        await _click_continue(page)
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass

                # Step 5: Job type
                try:
                    jtype_map = {
                        "FULL_TIME": "Full-time",
                        "PART_TIME": "Part-time",
                        "CONTRACT": "Contract",
                        "INTERNSHIP": "Internship",
                    }
                    jtype_label = jtype_map.get(job_type, "Full-time")
                    jtype_option = await _wait_for_any(page, [
                        f'label:has-text("{jtype_label}")',
                        f'input[value="{job_type}"]',
                        f'input[value="{jtype_label}"]',
                    ], timeout=5000)
                    if jtype_option:
                        await jtype_option.click()
                        await _click_continue(page)
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass

                # Step 6: Description — contenteditable div (Indeed uses rich text editor)
                desc_input = await _wait_for_any(page, [
                    'div[contenteditable="true"]',
                    'textarea[name="description"]',
                    'textarea[id="jobDescription"]',
                    '[data-testid="jobDescriptionInput"]',
                    '[role="textbox"]',
                ], timeout=15000)
                if desc_input:
                    await desc_input.click()
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Delete")
                    content_editable = await desc_input.get_attribute("contenteditable")
                    if content_editable:
                        await page.keyboard.type(description, delay=5)
                    else:
                        await desc_input.fill(description)
                    await _click_continue(page)
                    await page.wait_for_timeout(1500)

                # Step 7: Salary (optional)
                if salary_min or salary_max:
                    try:
                        min_input = await _wait_for_any(page, [
                            'input[name="salaryMin"]',
                            'input[id="salaryMin"]',
                            'input[placeholder*="minimum" i]',
                            'input[placeholder*="min" i]',
                        ], timeout=5000)
                        max_input = await _wait_for_any(page, [
                            'input[name="salaryMax"]',
                            'input[id="salaryMax"]',
                            'input[placeholder*="maximum" i]',
                            'input[placeholder*="max" i]',
                        ], timeout=3000)
                        if min_input and salary_min:
                            await min_input.fill(str(salary_min))
                        if max_input and salary_max:
                            await max_input.fill(str(salary_max))
                        await _click_continue(page)
                        await page.wait_for_timeout(1500)
                    except Exception:
                        pass

                # Step 8: Apply options (email)
                try:
                    email_option = await _wait_for_any(page, [
                        'label:has-text("email" i)',
                        'input[value="email"]',
                        '[data-testid*="email"]',
                    ], timeout=5000)
                    if email_option:
                        await email_option.click()

                    email_input = await _wait_for_any(page, [
                        'input[name="applyEmail"]',
                        'input[name="applicationEmail"]',
                        'input[type="email"]',
                        'input[placeholder*="email" i]',
                    ], timeout=5000)
                    if email_input:
                        await email_input.fill(apply_email)
                        await _click_continue(page)
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass

                # Step 9: Review & Post — find final Post button
                posted = False
                for btn_text in ["Post job", "Post Job", "Post now", "Publish", "Submit"]:
                    try:
                        btn = page.get_by_role("button", name=btn_text, exact=False)
                        if await btn.is_visible(timeout=4000):
                            await btn.click()
                            posted = True
                            break
                    except Exception:
                        continue

                if not posted:
                    try:
                        await page.click('button:has-text("Post")', timeout=5000)
                        posted = True
                    except Exception:
                        pass

                if not posted:
                    return json.dumps({
                        "success": False,
                        "error": "Could not find the Post button. Form may have been filled — check employers.indeed.com for a draft.",
                        "partial": True,
                        "current_url": page.url,
                    })

                await page.wait_for_timeout(3000)
                return json.dumps({
                    "success": True,
                    "message": f"Job '{title}' posted to Indeed Thailand.",
                    "url": page.url,
                    "note": "Job will appear in search results within a few hours.",
                })

            except Exception as e:
                page_url = page.url if page else "unknown"
                page_title = await page.title() if page else "unknown"
                return json.dumps({
                    "success": False,
                    "error": str(e),
                    "page_url": page_url,
                    "page_title": page_title,
                    "tip": "If page_title shows CAPTCHA or Access Denied, Indeed is blocking the cloud server IP.",
                })
            finally:
                await browser.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _indeed_login(page, email: str, password: str) -> None:
    """Log in to Indeed employer portal with stealth browser."""
    await page.goto(
        "https://secure.indeed.com/auth?hl=en&co=TH&continue=https%3A%2F%2Femployers.indeed.com%2F",
        wait_until="domcontentloaded",
        timeout=20000,
    )
    await page.wait_for_timeout(2000)

    page_title = await page.title()
    page_url = page.url

    # Step 1: email — confirmed selector from page inspection
    email_input = await _wait_for_any(page, [
        'input[name="__email"]',
        'input[type="email"]',
        'input[placeholder*="email" i]',
        'input[aria-label*="email" i]',
    ], timeout=12000)

    if not email_input:
        raise Exception(
            f"Email input not found. Page: '{page_title}' at {page_url}. "
            "Indeed may be showing a CAPTCHA or bot-detection page on this server IP."
        )

    await email_input.fill(email)
    await page.wait_for_timeout(500)

    # Click Continue (confirmed: button[type="submit"] with text "Continue")
    await page.click('button[type="submit"]')
    await page.wait_for_timeout(2000)

    # Step 2: password — confirmed: input[type="password"] (no name/id)
    pwd_input = await _wait_for_any(page, [
        'input[type="password"]',
        'input[name="__password"]',
        'input[name="password"]',
    ], timeout=10000)

    if not pwd_input:
        page_title = await page.title()
        raise Exception(
            f"Password input not found after email submission. "
            f"Page: '{page_title}' at {page.url}. "
            "Check if email is correct or if 2FA appeared."
        )

    await pwd_input.fill(password)
    await page.wait_for_timeout(500)
    await page.click('button[type="submit"]')

    # Wait for employer dashboard
    try:
        await page.wait_for_url("**/employers.indeed.com/**", timeout=15000)
    except Exception:
        page_title = await page.title()
        raise Exception(
            f"Login did not redirect to employer dashboard. "
            f"Page: '{page_title}' at {page.url}. "
            "Credentials may be wrong or additional verification required."
        )


async def _wait_for_any(page, selectors: list[str], timeout: int = 8000):
    """Try each selector and return the first visible one, or None."""
    per = max(timeout // len(selectors), 1500)
    for sel in selectors:
        try:
            el = page.locator(sel).first
            await el.wait_for(state="visible", timeout=per)
            return el
        except Exception:
            continue
    return None


async def _click_continue(page) -> None:
    """Click the Continue / Next button on the current step."""
    for btn_text in ["Continue", "Next", "Save and continue", "Save & continue"]:
        try:
            btn = page.get_by_role("button", name=btn_text, exact=False)
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await page.wait_for_timeout(1000)
                return
        except Exception:
            continue
    try:
        await page.click('button[type="submit"]', timeout=2000)
        await page.wait_for_timeout(1000)
    except Exception:
        pass


async def _screenshot_b64(page) -> str:
    """Take a screenshot and return as base64 string."""
    try:
        data = await page.screenshot(type="png")
        return base64.b64encode(data).decode()
    except Exception:
        return ""
