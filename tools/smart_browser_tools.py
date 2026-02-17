"""Smart Browser Tools — AI-vision-driven browser automation for any website.

The agent describes what it wants done in plain English. This tool:
  1. Opens the URL in a Playwright browser
  2. Takes a screenshot
  3. Sends the screenshot + task to Claude vision
  4. Claude returns the next action (click, type, scroll, etc.)
  5. Executes the action, loops until done
  6. If user input is needed (OTP, CAPTCHA) → pauses and returns session_id
  7. Saves session cookies per user+domain so login only happens once

Usage by the HR agent:
  result = browser_do_task(url="https://th.indeed.com/employers", task="Post a Padel Coach job...")
  if result["status"] == "needs_input":
      # Ask user for OTP / CAPTCHA, then:
      result = browser_provide_input(session_id=result["session_id"], value="482951")
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from typing import Optional
from urllib.parse import urlparse

from agno.tools import Toolkit

# ─────────────────────────────────────────────────────────────────────────────
# In-memory session state (lives for the duration of the process)
# Stores paused browser state when OTP / CAPTCHA is needed
# ─────────────────────────────────────────────────────────────────────────────
_SESSIONS: dict[str, dict] = {}

# ─────────────────────────────────────────────────────────────────────────────
# Vision prompt
# ─────────────────────────────────────────────────────────────────────────────
_VISION_SYSTEM = """You are controlling a web browser to complete a task.
You receive a screenshot of the current page and must decide the next action.

Reply with ONLY a JSON object — no markdown, no explanation, no code blocks.

Available actions:
{"action": "click", "x": 150, "y": 300, "description": "clicking the Submit button"}
{"action": "type", "text": "Padel Coach", "description": "typing the job title"}
{"action": "key", "key": "Tab", "description": "pressing Tab to move to next field"}
{"action": "scroll", "direction": "down", "pixels": 400, "description": "scrolling to see more fields"}
{"action": "wait", "seconds": 2, "description": "waiting for page to load"}
{"action": "navigate", "url": "https://...", "description": "navigating to a specific page"}
{"action": "done", "result": "Job posted successfully at https://...", "description": "task complete"}
{"action": "needs_input", "prompt": "Please enter the 6-digit code sent to your email", "description": "OTP required"}
{"action": "failed", "reason": "Could not find the job posting form after 5 attempts", "description": "giving up"}

Rules:
- Look at the screenshot carefully before acting
- If you're already logged in (no login form visible), go directly to the task
- If you see a login form, fill in credentials from the task context
- If you see an OTP / verification code field, use needs_input to ask the user
- If you see a CAPTCHA, use needs_input to ask the user to solve it
- Click a field before typing into it
- After filling a form, scroll down to check for more fields before submitting
- Prefer visible labeled buttons; use coordinates of the center of the element
- Use needs_input sparingly — only when genuinely blocked waiting for user
- Use failed only when the task is truly impossible (page not found, no form, etc.)
"""


def _vision_action(screenshot_b64: str, task: str, history: list[str]) -> dict:
    """Call Claude vision API to get the next browser action."""
    import anthropic

    client = anthropic.Anthropic()
    history_text = "\n".join(history[-8:]) if history else "No actions yet."

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=300,
        system=_VISION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": screenshot_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Task: {task}\n\n"
                            f"Actions taken so far:\n{history_text}\n\n"
                            "What is the next action?"
                        ),
                    },
                ],
            }
        ],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if the model accidentally adds them
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def _screenshot_b64(page) -> str:
    data = await page.screenshot(full_page=False, type="png")
    return base64.b64encode(data).decode()


async def _load_cookies(context, user_id: str | None, domain: str) -> None:
    if not user_id:
        return
    try:
        from tools.credential_tools import get_platform_session

        session = get_platform_session(user_id, domain)
        if session and session.get("cookies"):
            await context.add_cookies(session["cookies"])
    except Exception as e:
        print(f"[smart_browser] Could not load cookies for {domain}: {e}")


async def _save_cookies(context, user_id: str | None, domain: str) -> None:
    if not user_id:
        return
    try:
        from tools.credential_tools import save_platform_session

        cookies = await context.cookies()
        save_platform_session(user_id, domain, cookies)
    except Exception as e:
        print(f"[smart_browser] Could not save cookies for {domain}: {e}")


async def _new_browser_context(playwright):
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
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
    )
    await context.add_init_script(
        "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3]});"
        "window.chrome={runtime:{}};"
    )
    return browser, context


async def _execute_action(page, action: dict) -> None:
    """Execute a single vision-directed action on the page."""
    t = action.get("action")
    if t == "click":
        await page.mouse.click(action["x"], action["y"])
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
    elif t == "type":
        await page.keyboard.type(action["text"], delay=40)
    elif t == "key":
        await page.keyboard.press(action["key"])
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
    elif t == "scroll":
        px = action.get("pixels", 300)
        if action.get("direction") == "up":
            px = -px
        await page.evaluate(f"window.scrollBy(0, {px})")
    elif t == "wait":
        await asyncio.sleep(action.get("seconds", 1))
    elif t == "navigate":
        await page.goto(action["url"], wait_until="domcontentloaded", timeout=30000)


async def _run_vision_loop(
    page,
    context,
    task: str,
    history: list[str],
    user_id: str | None,
    domain: str,
    session_id: str,
    max_steps: int = 30,
) -> dict:
    """Core vision loop — runs until done / needs_input / failed / max_steps."""
    for step in range(max_steps):
        shot = await _screenshot_b64(page)
        try:
            action = _vision_action(shot, task, history)
        except Exception as e:
            return {"status": "failed", "reason": f"Vision API error: {e}"}

        action_type = action.get("action", "")
        desc = action.get("description", "")
        history.append(f"Step {step + 1}: {action_type} — {desc}")
        print(f"[smart_browser] {history[-1]}")

        if action_type == "done":
            await _save_cookies(context, user_id, domain)
            return {
                "status": "success",
                "result": action.get("result", "Task completed successfully."),
                "session_id": session_id,
            }

        if action_type == "needs_input":
            # Pause: save cookies + current URL so we can resume
            cookies = await context.cookies()
            _SESSIONS[session_id] = {
                "cookies": cookies,
                "url": page.url,
                "task": task,
                "domain": domain,
                "user_id": user_id,
                "history": list(history),
                "pending_input": None,
            }
            return {
                "status": "needs_input",
                "prompt": action.get("prompt", "Please provide the required input."),
                "session_id": session_id,
            }

        if action_type == "failed":
            return {
                "status": "failed",
                "reason": action.get("reason", "Task could not be completed."),
                "session_id": session_id,
            }

        # Execute normal action
        try:
            await _execute_action(page, action)
        except Exception as e:
            history.append(f"  ⚠ Action error: {e}")

    return {
        "status": "failed",
        "reason": f"Reached maximum steps ({max_steps}) without completing the task.",
        "session_id": session_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Toolkit
# ─────────────────────────────────────────────────────────────────────────────


class SmartBrowserTools(Toolkit):
    """AI-vision browser that navigates any website on behalf of the user.

    The agent describes what it wants done; this tool figures out how to do it
    by looking at screenshots, just like a human would.
    """

    def __init__(self, user_id: str | None = None):
        super().__init__(name="smart_browser")
        self.user_id = user_id
        self.register(self.browser_do_task)
        self.register(self.browser_provide_input)

    # ── Public tools ─────────────────────────────────────────────────────────

    def browser_do_task(
        self,
        url: str,
        task: str,
        session_id: str | None = None,
    ) -> str:
        """Open a URL and complete a task using AI vision — works on any website.

        The browser takes screenshots, decides what to click or type, and keeps
        going until the task is done. If it needs user input (e.g. a one-time
        code sent to their email), it pauses and returns a session_id so the
        agent can ask the user and then call browser_provide_input to resume.

        Saved sessions: after a successful login, cookies are stored in Supabase
        so future calls to the same domain skip the login entirely.

        Args:
            url:        The URL to start at (e.g. 'https://th.indeed.com/employers').
            task:       Plain-English description of what to do. Include any
                        credentials the agent already knows (email, job details, etc.)
                        so the browser can fill them in automatically.
            session_id: Pass a session_id returned by a previous needs_input
                        response to resume a paused session.

        Returns:
            JSON string with:
              status      — 'success' | 'needs_input' | 'failed'
              result      — (on success) human-readable outcome
              prompt      — (on needs_input) what to ask the user
              session_id  — use this in browser_provide_input to resume
              reason      — (on failed) why it couldn't complete
        """
        return asyncio.run(self._do_task(url, task, session_id))

    def browser_provide_input(self, session_id: str, value: str) -> str:
        """Resume a paused browser session by providing the requested input.

        Call this after browser_do_task returns status='needs_input'. Pass the
        session_id from that response and the value the user provided (e.g. the
        OTP code sent to their email, or a CAPTCHA answer).

        Args:
            session_id: The session_id from the paused browser_do_task call.
            value:      The input value (e.g. '482951' for a 6-digit OTP).

        Returns:
            JSON string with the same schema as browser_do_task.
        """
        session = _SESSIONS.get(session_id)
        if not session:
            return json.dumps({
                "status": "failed",
                "reason": f"Session '{session_id}' not found or already completed.",
            })
        session["pending_input"] = value
        return asyncio.run(self._resume(session_id))

    # ── Async internals ───────────────────────────────────────────────────────

    async def _do_task(
        self, url: str, task: str, session_id: str | None
    ) -> str:
        domain = urlparse(url).netloc
        sid = session_id or str(uuid.uuid4())

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser, context = await _new_browser_context(p)
            await _load_cookies(context, self.user_id, domain)
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                await browser.close()
                return json.dumps({"status": "failed", "reason": f"Could not open {url}: {e}"})

            result = await _run_vision_loop(
                page, context, task, [], self.user_id, domain, sid
            )
            await browser.close()
        return json.dumps(result)

    async def _resume(self, session_id: str) -> str:
        session = _SESSIONS.pop(session_id)
        domain = session["domain"]
        user_id = session["user_id"]
        task = session["task"]
        history = session.get("history", [])
        pending_input = session.get("pending_input", "")

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser, context = await _new_browser_context(p)
            if session.get("cookies"):
                await context.add_cookies(session["cookies"])

            page = await context.new_page()
            try:
                await page.goto(session["url"], wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                await browser.close()
                return json.dumps({"status": "failed", "reason": f"Could not resume: {e}"})

            # Type the user-provided input into whatever field is focused/visible
            if pending_input:
                await page.keyboard.type(pending_input, delay=40)
                await page.keyboard.press("Enter")
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=8000)
                except Exception:
                    pass

            history.append(f"Resumed: provided user input ({len(pending_input)} chars)")
            result = await _run_vision_loop(
                page, context, task, history, user_id, domain, session_id, max_steps=20
            )
            await browser.close()
        return json.dumps(result)
