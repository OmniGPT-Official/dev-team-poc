"""
Simple global user context for tracking current user_id in workflows.

Usage:
    # At API/entry point:
    set_current_user_id("user-uuid-here")

    # In workflows/tools:
    user_id = get_current_user_id()
"""

import contextvars
from typing import Optional

# Context variable for user_id (safe for async/concurrent requests)
# Unlike threading.local(), contextvars work correctly with asyncio
_user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'user_id', default=None
)


def set_current_user_id(user_id: str) -> None:
    """Set the current user_id for this async context."""
    _user_id_var.set(user_id)
    print(f"[user_context] Set user_id: {user_id}")


def get_current_user_id() -> Optional[str]:
    """Get the current user_id for this async context."""
    user_id = _user_id_var.get()
    return user_id


def clear_current_user_id() -> None:
    """Clear the current user_id (cleanup after request)."""
    _user_id_var.set(None)
