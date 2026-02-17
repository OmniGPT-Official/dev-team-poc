"""Generic Job Board Tools — agent-facing Toolkit for multi-platform job posting.

Exposes 4 tools to the HR Job Poster agent:
  - list_job_boards        : see all available platforms + credential status
  - check_job_board_setup  : check credentials for a specific platform
  - post_job_to_board      : post a job (checks credentials first)
  - check_board_login      : test login without posting (for debugging)
"""

from __future__ import annotations

import asyncio
import json

from agno.tools import Toolkit


class GenericJobBoardTools(Toolkit):
    """Agent-facing tools for multi-platform job posting."""

    def __init__(self):
        super().__init__(name="generic_job_boards")
        self.register(self.list_job_boards)
        self.register(self.check_job_board_setup)
        self.register(self.post_job_to_board)
        self.register(self.check_board_login)

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def list_job_boards(self) -> str:
        """List all available job boards and their credential status.

        Returns:
            JSON array with id, name, country, status, and missing vars for each board.
        """
        from tools.job_boards import BOARD_REGISTRY

        boards = []
        for board_id, board in BOARD_REGISTRY.items():
            cred_check = board.check_credentials()
            boards.append({
                "id": board_id,
                "name": board.name,
                "country": board.country,
                "status": "ready" if cred_check["configured"] else "missing_credentials",
                "missing_env_vars": cred_check["missing"],
            })

        if not boards:
            return json.dumps({
                "boards": [],
                "message": "No job board plugins are installed yet.",
            })

        return json.dumps({"boards": boards})

    def check_job_board_setup(self, board_id: str) -> str:
        """Check credential status for a specific job board.

        Args:
            board_id: The board identifier (e.g. 'indeed_th').

        Returns:
            JSON with configured status, missing env vars, and Railway setup instructions.
        """
        from tools.job_boards import BOARD_REGISTRY

        board = BOARD_REGISTRY.get(board_id)
        if not board:
            available = list(BOARD_REGISTRY.keys())
            return json.dumps({
                "error": f"Board '{board_id}' not found.",
                "available_boards": available,
                "message": (
                    f"I don't have '{board_id}' set up yet. "
                    f"Available boards: {', '.join(available) if available else 'none'}."
                ),
            })

        cred_check = board.check_credentials()

        if cred_check["configured"]:
            return json.dumps({
                "board_id": board_id,
                "name": board.name,
                "status": "ready",
                "message": f"{board.name} is fully configured and ready to post.",
            })

        missing = cred_check["missing"]
        instructions = (
            f"{board.name} needs the following env vars added in Railway:\n"
            + "\n".join(f"  - {v}" for v in missing)
            + "\n\nTo add them:\n"
            "  1. Go to Railway → your project → Variables\n"
            "  2. Add each variable above\n"
            "  3. Railway will auto-redeploy — posting will work immediately after."
        )

        return json.dumps({
            "board_id": board_id,
            "name": board.name,
            "status": "missing_credentials",
            "missing_env_vars": missing,
            "setup_instructions": instructions,
        })

    def post_job_to_board(
        self,
        board_id: str,
        title: str,
        description: str,
        location: str,
        apply_email: str,
        job_type: str = "FULL_TIME",
        salary_min: int | None = None,
        salary_max: int | None = None,
        company: str = "",
    ) -> str:
        """Post a job to a specific job board.

        Checks credentials first and returns a clear error if anything is missing.

        Args:
            board_id: The board identifier (e.g. 'indeed_th').
            title: Job title (e.g. 'Padel Coach').
            description: Full job description in plain text.
            location: Location string (e.g. 'Bangkok, Thailand').
            apply_email: Email address for applications.
            job_type: FULL_TIME | PART_TIME | CONTRACT | INTERNSHIP.
            salary_min: Minimum monthly salary in local currency (optional).
            salary_max: Maximum monthly salary in local currency (optional).
            company: Company name (optional — often auto-filled from the account).

        Returns:
            JSON with success status, job URL on success, or error details.
        """
        from tools.job_boards import BOARD_REGISTRY

        board = BOARD_REGISTRY.get(board_id)
        if not board:
            available = list(BOARD_REGISTRY.keys())
            return json.dumps({
                "success": False,
                "error": f"Board '{board_id}' is not installed.",
                "available_boards": available,
                "message": (
                    f"I don't have '{board_id}' set up yet. "
                    f"Available: {', '.join(available) if available else 'none'}."
                ),
            })

        # Credential check before attempting to post
        cred_check = board.check_credentials()
        if not cred_check["configured"]:
            missing = cred_check["missing"]
            return json.dumps({
                "success": False,
                "error": "Missing credentials",
                "board_id": board_id,
                "name": board.name,
                "missing_env_vars": missing,
                "message": (
                    f"{board.name} needs these Railway env vars before I can post:\n"
                    + "\n".join(f"  - {v}" for v in missing)
                ),
            })

        job_data = {
            "title": title,
            "description": description,
            "location": location,
            "apply_email": apply_email,
            "job_type": job_type,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "company": company,
        }

        try:
            from playwright.async_api import async_playwright

            async def _run():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
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
                    page = await context.new_page()
                    try:
                        await board.login(page)
                        result = await board.post_job(page, job_data)
                        return result
                    finally:
                        await browser.close()

            result = asyncio.run(_run())
            return json.dumps(result)

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "board_id": board_id,
            })

    def check_board_login(self, board_id: str) -> str:
        """Test login for a specific board without posting (for debugging).

        Args:
            board_id: The board identifier (e.g. 'indeed_th').

        Returns:
            JSON with login success/failure and any debug info.
        """
        from tools.job_boards import BOARD_REGISTRY

        board = BOARD_REGISTRY.get(board_id)
        if not board:
            return json.dumps({
                "success": False,
                "error": f"Board '{board_id}' not found.",
                "available_boards": list(BOARD_REGISTRY.keys()),
            })

        cred_check = board.check_credentials()
        if not cred_check["configured"]:
            return json.dumps({
                "success": False,
                "error": "Cannot test login — credentials missing.",
                "missing_env_vars": cred_check["missing"],
            })

        # For indeed_th, delegate to the existing check_indeed_login tool
        if board_id == "indeed_th":
            from tools.browser_posting_tools import IndeedBrowserPosterTools
            import os
            poster = IndeedBrowserPosterTools(
                email=os.getenv("INDEED_EMAIL", ""),
                password=os.getenv("INDEED_PASSWORD", ""),
            )
            return poster.check_indeed_login()

        return json.dumps({
            "success": True,
            "message": f"Credentials for {board.name} are set. Login test not implemented for this board.",
        })
