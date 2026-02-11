"""Email Tracker - Prevent duplicate email sends

This utility provides session-level tracking to prevent accidentally
sending duplicate emails to the same recipient.

Usage:
    from utils.email_tracker import mark_email_sent, check_email_sent

    if check_email_sent("contact@example.com"):
        print("Already sent!")
    else:
        send_email(...)
        mark_email_sent("contact@example.com")
"""

from typing import Set
from datetime import datetime


class EmailTracker:
    """Track sent emails within a session to prevent duplicates"""

    def __init__(self):
        self.sent_emails: Set[str] = set()
        self.session_start = datetime.now()

    def mark_sent(self, email: str) -> None:
        """Mark an email address as sent

        Args:
            email: Email address that was sent to
        """
        normalized = email.lower().strip()
        self.sent_emails.add(normalized)

    def was_sent(self, email: str) -> bool:
        """Check if email was already sent this session

        Args:
            email: Email address to check

        Returns:
            True if email was already sent, False otherwise
        """
        normalized = email.lower().strip()
        return normalized in self.sent_emails

    def get_sent_count(self) -> int:
        """Get total number of emails sent this session

        Returns:
            Count of unique email addresses sent to
        """
        return len(self.sent_emails)

    def get_sent_list(self) -> list[str]:
        """Get list of all sent email addresses

        Returns:
            List of email addresses that were sent to
        """
        return sorted(list(self.sent_emails))

    def reset(self) -> None:
        """Reset tracker (clear all sent emails)"""
        self.sent_emails.clear()
        self.session_start = datetime.now()


# Global tracker instance
_tracker = EmailTracker()


def mark_email_sent(email: str) -> None:
    """Mark an email as sent (convenience function)

    Args:
        email: Email address that was sent to
    """
    _tracker.mark_sent(email)


def check_email_sent(email: str) -> bool:
    """Check if email already sent (convenience function)

    Args:
        email: Email address to check

    Returns:
        True if already sent, False otherwise
    """
    return _tracker.was_sent(email)


def get_sent_count() -> int:
    """Get count of sent emails (convenience function)

    Returns:
        Number of unique emails sent this session
    """
    return _tracker.get_sent_count()


def get_sent_list() -> list[str]:
    """Get list of sent emails (convenience function)

    Returns:
        List of email addresses sent to
    """
    return _tracker.get_sent_list()


def reset_tracker() -> None:
    """Reset the tracker (convenience function)"""
    _tracker.reset()
