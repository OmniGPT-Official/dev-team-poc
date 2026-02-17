"""Job board plugin registry.

Drop a new file into this directory — it's auto-discovered and immediately
available to the HR Job Poster agent. No other files need to change.

Example: tools/job_boards/jobth.py
    @register_board
    class JobTH(JobBoardBase):
        board_id = "jobth"
        name = "JobTH"
        country = "TH"
        required_env_vars = ["JOBTH_EMAIL", "JOBTH_PASSWORD"]
        ...
"""

from __future__ import annotations

import importlib
import os
import pkgutil
from abc import ABC, abstractmethod

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BOARD_REGISTRY: dict[str, "JobBoardBase"] = {}


def register_board(cls: type) -> type:
    """Class decorator — registers the plugin in BOARD_REGISTRY by board_id."""
    BOARD_REGISTRY[cls.board_id] = cls()
    return cls


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class JobBoardBase(ABC):
    """Abstract base for every job board plugin.

    Subclass, set class attributes, implement ``login`` and ``post_job``,
    then decorate with ``@register_board``.
    """

    board_id: str          # e.g. "indeed_th"
    name: str              # e.g. "Indeed Thailand"
    country: str           # ISO-3166-1 alpha-2, e.g. "TH"
    required_env_vars: list[str]  # e.g. ["INDEED_EMAIL", "GMAIL_APP_PASSWORD"]

    # Supabase credential keys for per-user storage.
    # Map from internal key → Supabase provider name stored in user_api_keys.
    # e.g. {"email": "indeed_email", "gmail_app_password": "gmail_app_password"}
    credential_keys: dict[str, str] = {}

    def get_user_credentials(self, user_id: str | None) -> dict:
        """Fetch per-user credentials from Supabase.

        Falls back to env vars if user has no Supabase credentials stored.

        Returns:
            dict of key → value for each credential_key defined on the board.
        """
        if not user_id or not self.credential_keys:
            return {}
        try:
            from services.api_key_store import get_api_key
            return {
                key: get_api_key(user_id, provider)
                for key, provider in self.credential_keys.items()
            }
        except Exception:
            return {}

    def check_credentials(self, user_id: str | None = None) -> dict:
        """Return credential status for this board.

        Checks Supabase first (per-user), falls back to env vars.

        Returns:
            {
                "configured": bool,
                "missing": ["VAR1", ...],   # empty if all set
                "source": "supabase" | "env_vars"
            }
        """
        # Check Supabase credentials first
        if user_id and self.credential_keys:
            user_creds = self.get_user_credentials(user_id)
            missing = [k for k, v in user_creds.items() if not v]
            if not missing:
                return {"configured": True, "missing": [], "source": "supabase"}

        # Fall back to env vars
        missing = [v for v in self.required_env_vars if not os.getenv(v, "")]
        return {
            "configured": not missing,
            "missing": missing,
            "source": "env_vars",
        }

    @abstractmethod
    async def login(self, page, credentials: dict) -> None:
        """Log in to the employer portal on *page* (Playwright Page).

        Args:
            credentials: dict of credential values (from Supabase or env vars).
        """
        ...

    @abstractmethod
    async def post_job(self, page, job_data: dict, credentials: dict) -> dict:
        """Post the job described by *job_data* on *page*.

        Args:
            credentials: dict of credential values (from Supabase or env vars).

        Returns:
            {"success": bool, "url": str | None, "error": str | None}
        """
        ...


# ---------------------------------------------------------------------------
# Auto-discover all plugins in this package
# ---------------------------------------------------------------------------

# Import every module in tools/job_boards/ so @register_board decorators run.
for _finder, _modname, _ispkg in pkgutil.iter_modules(__path__):
    importlib.import_module(f"tools.job_boards.{_modname}")
