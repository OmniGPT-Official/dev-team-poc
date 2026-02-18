"""Extended Browserbase Tools — adds execute_javascript to the native BrowserbaseTools.

The 4 native tools (navigate_to, get_page_content, screenshot, close_session) let the
agent navigate and read pages. execute_javascript lets the agent actually interact:
fill form fields, click buttons, submit forms — anything doable with JS.

Typical flow for posting a job:
  1. navigate_to(url)         — go to the job posting page
  2. get_page_content()       — read page HTML to find form field IDs/names
  3. execute_javascript(...)  — fill in title, description, location etc.
  4. execute_javascript(...)  — click submit
  5. get_page_content()       — verify success
  6. close_session()
"""

from __future__ import annotations

import json
from typing import Optional

from agno.tools.browserbase import BrowserbaseTools


class BrowserbaseInteractiveTools(BrowserbaseTools):
    """BrowserbaseTools extended with execute_javascript for form interaction."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register(self.execute_javascript)

    def execute_javascript(self, script: str) -> str:
        """Execute JavaScript on the current browser page.

        Use this to interact with the page: fill form fields, click buttons,
        submit forms. The agent should first call get_page_content() to find
        the correct element selectors, then use this tool to interact.

        Common patterns:
          Fill a text field:
            document.querySelector('#job-title').value = 'Padel Coach'
          Fill by name attribute:
            document.querySelector('[name="title"]').value = 'Padel Coach'
          Click a button:
            document.querySelector('#submit-btn').click()
          Select a dropdown option:
            document.querySelector('#job-type').value = 'FULL_TIME'
          Check the result after filling:
            document.querySelector('#job-title').value

        Args:
            script: JavaScript code to execute on the page.

        Returns:
            JSON with the return value of the script, or error details.
        """
        try:
            if not getattr(self, '_page', None):
                return json.dumps({"error": "No active browser page. Call navigate_to(url) first."})
            result = self._page.evaluate(script)
            return json.dumps({"result": str(result) if result is not None else "null"})
        except Exception as e:
            return json.dumps({"error": str(e)})
