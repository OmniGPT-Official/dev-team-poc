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
import json
import os
from typing import Optional

from agno.tools import Toolkit


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
            JSON with login status.
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
                         The HTML version is not needed — Indeed handles formatting.
            location: Location string (e.g. "Bangkok, Thailand")
            apply_email: Email address where candidates apply
            company: Company name (usually auto-filled from Indeed account)
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
                "fix": "Ask admin to run: railway variables set INDEED_EMAIL=... INDEED_PASSWORD=...",
            })

        return asyncio.run(self._post_job_async(
            title, description, location, apply_email, company, job_type, salary_min, salary_max,
        ))

    # ------------------------------------------------------------------
    # Async implementation
    # ------------------------------------------------------------------

    async def _check_login_async(self) -> str:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return json.dumps({"success": False, "error": "playwright not installed"})

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            try:
                await _indeed_login(page, self.email, self.password)
                return json.dumps({"success": True, "message": "Login successful."})
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})
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
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = await context.new_page()
            try:
                # Step 1: Login
                await _indeed_login(page, self.email, self.password)

                # Step 2: Go to post job page
                await page.goto(
                    "https://employers.indeed.com/jobs/post",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )

                # Step 3: Job Title
                title_input = await _wait_for_any(page, [
                    'input[id="jobTitle"]',
                    'input[name="jobTitle"]',
                    'input[placeholder*="title" i]',
                    'input[aria-label*="title" i]',
                ], timeout=15000)
                if not title_input:
                    raise Exception("Could not find job title input. Indeed UI may have changed.")
                await title_input.fill(title)
                await _click_continue(page)

                # Step 4: Location (may be pre-filled or combined with title step)
                try:
                    loc_input = await _wait_for_any(page, [
                        'input[id="location"]',
                        'input[name="location"]',
                        'input[placeholder*="location" i]',
                        'input[aria-label*="location" i]',
                    ], timeout=8000)
                    if loc_input:
                        await loc_input.fill("")
                        await loc_input.fill(location)
                        await page.wait_for_timeout(1000)  # let autocomplete load
                        # Press Enter to accept first suggestion or just continue
                        await page.keyboard.press("Escape")
                        await _click_continue(page)
                except Exception:
                    pass  # Location might be on same step as description

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
                        f'[data-testid*="jobType"]',
                        f'input[value="{job_type}"]',
                    ], timeout=5000)
                    if jtype_option:
                        await jtype_option.click()
                        await _click_continue(page)
                except Exception:
                    pass  # Job type might be optional or on different step

                # Step 6: Description
                desc_input = await _wait_for_any(page, [
                    'div[contenteditable="true"]',
                    'textarea[id="jobDescription"]',
                    'textarea[name="description"]',
                    '[data-testid="jobDescriptionInput"]',
                ], timeout=15000)
                if desc_input:
                    await desc_input.click()
                    # Clear existing content and type description
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Delete")
                    await desc_input.fill(description) if await desc_input.get_attribute("contenteditable") is None else None
                    if await desc_input.get_attribute("contenteditable"):
                        await page.keyboard.type(description)
                    await _click_continue(page)

                # Step 7: Salary (optional)
                if salary_min or salary_max:
                    try:
                        min_input = await _wait_for_any(page, [
                            'input[name="salaryMin"]',
                            'input[id="salaryMin"]',
                            'input[placeholder*="minimum" i]',
                        ], timeout=5000)
                        max_input = await _wait_for_any(page, [
                            'input[name="salaryMax"]',
                            'input[id="salaryMax"]',
                            'input[placeholder*="maximum" i]',
                        ], timeout=3000)
                        if min_input and salary_min:
                            await min_input.fill(str(salary_min))
                        if max_input and salary_max:
                            await max_input.fill(str(salary_max))
                        await _click_continue(page)
                    except Exception:
                        pass  # Salary is optional

                # Step 8: Apply options (email)
                try:
                    email_input = await _wait_for_any(page, [
                        'input[name="applyEmail"]',
                        'input[type="email"]',
                        'input[placeholder*="email" i]',
                        'input[aria-label*"email" i]',
                    ], timeout=8000)
                    if email_input:
                        await email_input.fill(apply_email)
                        await _click_continue(page)
                except Exception:
                    pass

                # Step 9: Review & Post — click the final Post/Submit button
                posted = False
                for btn_text in ["Post job", "Post Job", "Submit", "Publish"]:
                    try:
                        btn = page.get_by_role("button", name=btn_text)
                        if await btn.is_visible(timeout=5000):
                            await btn.click()
                            posted = True
                            break
                    except Exception:
                        continue

                if not posted:
                    # Try any button with "post" in it
                    try:
                        await page.click('button:has-text("Post")', timeout=5000)
                        posted = True
                    except Exception:
                        pass

                if not posted:
                    return json.dumps({
                        "success": False,
                        "error": "Could not find the final Post button. Job form was filled but not submitted.",
                        "partial": True,
                        "note": "Indeed UI may have changed. The job details were filled in — check employers.indeed.com for a draft.",
                    })

                # Wait for confirmation
                await page.wait_for_timeout(3000)
                final_url = page.url

                return json.dumps({
                    "success": True,
                    "message": f"Job '{title}' posted to Indeed Thailand.",
                    "url": final_url,
                    "note": "Job may take a few hours to appear in search results.",
                })

            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e),
                    "tip": "Check INDEED_EMAIL / INDEED_PASSWORD in Railway env vars.",
                })
            finally:
                await browser.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _indeed_login(page, email: str, password: str) -> None:
    """Log in to Indeed employer portal."""
    from playwright.async_api import Page
    await page.goto(
        "https://secure.indeed.com/auth?hl=en&co=TH&continue=https%3A%2F%2Femployers.indeed.com%2F",
        wait_until="domcontentloaded",
        timeout=20000,
    )
    # Step 1: email
    email_input = await _wait_for_any(page, [
        'input[name="__email"]',
        'input[type="email"]',
        'input[id="input-email-address"]',
        'input[placeholder*="email" i]',
    ], timeout=15000)
    if not email_input:
        raise Exception("Could not find email input on Indeed login page.")
    await email_input.fill(email)
    await _click_continue(page)

    # Step 2: password
    await page.wait_for_timeout(1500)
    pwd_input = await _wait_for_any(page, [
        'input[name="__password"]',
        'input[type="password"]',
        'input[id="input-password"]',
    ], timeout=10000)
    if not pwd_input:
        raise Exception("Could not find password input. Check if 2FA is required or login failed.")
    await pwd_input.fill(password)
    await _click_continue(page)

    # Wait for employer dashboard
    await page.wait_for_url("**/employers.indeed.com/**", timeout=15000)


async def _wait_for_any(page, selectors: list[str], timeout: int = 8000):
    """Try each selector and return the first one found, or None."""
    per = timeout // len(selectors)
    for sel in selectors:
        try:
            el = page.locator(sel).first
            await el.wait_for(state="visible", timeout=per)
            return el
        except Exception:
            continue
    return None


async def _click_continue(page) -> None:
    """Click the Continue / Next / Submit button on the current step."""
    for btn_text in ["Continue", "Next", "Submit", "Save and continue"]:
        try:
            btn = page.get_by_role("button", name=btn_text)
            if await btn.is_visible(timeout=3000):
                await btn.click()
                await page.wait_for_timeout(1500)
                return
        except Exception:
            continue
    # Fallback: any submit button
    try:
        await page.click('button[type="submit"]', timeout=3000)
        await page.wait_for_timeout(1500)
    except Exception:
        pass
