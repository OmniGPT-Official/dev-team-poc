"""
Project Context Manager

Tracks the current project_id throughout workflow execution using contextvars.
Similar to user_context.py but for project tracking.

Usage:
    # At workflow start:
    set_current_project_id("project-uuid-here")

    # In tools/agents:
    project_id = get_current_project_id()

    # Clear after workflow:
    clear_current_project_id()
"""

import contextvars
from typing import Optional

# Context variable for project_id (safe for async/concurrent requests)
_project_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'project_id', default=None
)


def set_current_project_id(project_id: str) -> None:
    """Set the current project_id for this async context."""
    _project_id_var.set(project_id)
    print(f"[project_context] Set project_id: {project_id}")


def get_current_project_id() -> Optional[str]:
    """Get the current project_id for this async context."""
    project_id = _project_id_var.get()
    return project_id


def clear_current_project_id() -> None:
    """Clear the current project_id (cleanup after workflow)."""
    _project_id_var.set(None)
    print(f"[project_context] Cleared project_id")
