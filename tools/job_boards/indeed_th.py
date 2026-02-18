"""Indeed Thailand job board plugin.

Credentials lookup order:
  1. Supabase (per-user) — stored via Credentials Manager agent
  2. Env vars fallback   — INDEED_EMAIL + GMAIL_APP_PASSWORD
"""

from __future__ import annotations

import os

from tools.job_boards import JobBoardBase, register_board


@register_board
class IndeedTH(JobBoardBase):
    board_id = "indeed_th"
    name = "Indeed Thailand"
    country = "TH"
    required_env_vars = ["INDEED_EMAIL", "GMAIL_APP_PASSWORD"]

    # Maps internal key → Supabase provider name in user_api_keys table
    credential_keys = {
        "email": "indeed_email",
        "gmail_app_password": "gmail_app_password",
    }

    def _resolve(self, credentials: dict) -> tuple[str, str]:
        """Return (email, gmail_app_password) from Supabase or env var fallback."""
        email = credentials.get("email") or os.getenv("INDEED_EMAIL", "")
        gmail_app_pw = credentials.get("gmail_app_password") or os.getenv("GMAIL_APP_PASSWORD", "")
        return email, gmail_app_pw

    async def login(self, page, credentials: dict) -> None:
        from tools.browser_posting_tools import _indeed_login
        email, _ = self._resolve(credentials)
        password = os.getenv("INDEED_PASSWORD", "")
        await _indeed_login(page, email, password)

    async def post_job(self, page, job_data: dict, credentials: dict) -> dict:
        import json
        from tools.browser_posting_tools import IndeedBrowserPosterTools

        email, _ = self._resolve(credentials)
        poster = IndeedBrowserPosterTools(
            email=email,
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
