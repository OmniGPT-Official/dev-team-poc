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

    def check_credentials(self) -> dict:
        """Return credential status for this board.

        Returns:
            {
                "configured": bool,
                "missing": ["VAR1", ...],   # empty if all set
            }
        """
        missing = [v for v in self.required_env_vars if not os.getenv(v, "")]
        return {"configured": not missing, "missing": missing}

    @abstractmethod
    async def login(self, page) -> None:
        """Log in to the employer portal on *page* (Playwright Page)."""
        ...

    @abstractmethod
    async def post_job(self, page, job_data: dict) -> dict:
        """Post the job described by *job_data* on *page*.

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
