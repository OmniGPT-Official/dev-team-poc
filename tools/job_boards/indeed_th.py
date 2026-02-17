"""Indeed Thailand job board plugin.

Wraps the existing IndeedBrowserPosterTools from browser_posting_tools.py.
"""

from __future__ import annotations

import asyncio
import os

from tools.job_boards import JobBoardBase, register_board


@register_board
class IndeedTH(JobBoardBase):
    board_id = "indeed_th"
    name = "Indeed Thailand"
    country = "TH"
    required_env_vars = ["INDEED_EMAIL", "GMAIL_APP_PASSWORD"]

    async def login(self, page) -> None:
        """Delegates to the shared _indeed_login helper."""
        from tools.browser_posting_tools import _indeed_login
        email = os.getenv("INDEED_EMAIL", "")
        password = os.getenv("INDEED_PASSWORD", "")
        await _indeed_login(page, email, password)

    async def post_job(self, page, job_data: dict) -> dict:
        """Post a job using the existing IndeedBrowserPosterTools logic."""
        from tools.browser_posting_tools import IndeedBrowserPosterTools
        import json

        poster = IndeedBrowserPosterTools(
            email=os.getenv("INDEED_EMAIL", ""),
            password=os.getenv("INDEED_PASSWORD", ""),
        )
        result_json = poster.post_job_to_indeed(
            title=job_data.get("title", ""),
            description=job_data.get("description", ""),
            location=job_data.get("location", "Bangkok, Thailand"),
            apply_email=job_data.get("apply_email", ""),
            company=job_data.get("company", ""),
            job_type=job_data.get("job_type", "FULL_TIME"),
            salary_min=job_data.get("salary_min"),
            salary_max=job_data.get("salary_max"),
        )
        return json.loads(result_json)
