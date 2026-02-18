"""Generic Job Board Tools — agent-facing Toolkit for job board discovery.

Exposes 2 read-only tools to the HR Job Poster agent:
  - list_job_boards        : see all available platforms + credential status
  - check_job_board_setup  : check credentials for a specific platform

NOTE: Actual job posting is handled via Browserbase browser tools (navigate_to, etc.).
The previous post_job_to_board / check_board_login methods used local Playwright which
is blocked by Cloudflare on Railway — they have been removed.
"""

from __future__ import annotations

import json

from agno.tools import Toolkit


class GenericJobBoardTools(Toolkit):
    """Agent-facing tools for job board discovery (read-only)."""

    def __init__(self, user_id: str | None = None):
        super().__init__(name="generic_job_boards")
        self.user_id = user_id
        self.register(self.list_job_boards)
        self.register(self.check_job_board_setup)

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
            cred_check = board.check_credentials(self.user_id)
            boards.append({
                "id": board_id,
                "name": board.name,
                "country": board.country,
                "status": "ready" if cred_check["configured"] else "missing_credentials",
                "missing_env_vars": cred_check["missing"],
                "credential_source": cred_check.get("source", "env_vars"),
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

        cred_check = board.check_credentials(self.user_id)

        if cred_check["configured"]:
            source = cred_check.get("source", "env_vars")
            return json.dumps({
                "board_id": board_id,
                "name": board.name,
                "status": "ready",
                "credential_source": source,
                "message": f"{board.name} is fully configured and ready to post.",
            })

        missing = cred_check["missing"]
        # Guide user to save credentials via the Credentials Manager agent
        instructions = (
            f"{board.name} credentials are not set up yet.\n\n"
            "To set them up, tell me:\n"
            "  'Save my Indeed credentials' and provide your Indeed email and Gmail App Password.\n\n"
            "I'll store them securely so you never need to do this again."
        )

        return json.dumps({
            "board_id": board_id,
            "name": board.name,
            "status": "missing_credentials",
            "missing_env_vars": missing,
            "setup_instructions": instructions,
        })
