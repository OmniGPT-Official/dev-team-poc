"""Per-request user context using contextvars.

The pre-hook (tool_injector) sets the current user_id when an agent run starts.
Workflow steps read it to fetch per-user API keys from the database.
"""

import contextvars
from typing import Optional

_current_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_user_id", default=None
)


def set_current_user_id(user_id: str) -> None:
    """Set the current user_id (called from pre-hook)."""
    _current_user_id.set(user_id)


def get_current_user_id() -> Optional[str]:
    """Get the current user_id (called from workflow steps)."""
    return _current_user_id.get()
