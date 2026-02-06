"""
Gmail Tools for Email Follow-Up Workflow

These tools enable searching email history, sending emails,
and validating email addresses.
"""

from agno.tools import tool
from typing import List, Dict, Any, Optional
import re


@tool(show_result=True)
def search_gmail_history(
    recipient_email: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    Search Gmail for conversation history with a specific email address.

    Args:
        recipient_email: Email address to search for
        max_results: Maximum number of emails to return

    Returns:
        List of email threads with subject, date, and snippet
    """
    # TODO: Implement with Gmail API when credentials are set up
    # For now, return sample data for testing
    return [
        {
            "subject": "Re: Demo discussion",
            "date": "2026-01-28",
            "snippet": "Thanks for the demo yesterday. We're interested in moving forward..."
        },
        {
            "subject": "Conference follow-up",
            "date": "2026-01-20",
            "snippet": "Great meeting you at the conference. Let's schedule a time to discuss..."
        }
    ]


@tool(show_result=True)
def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send an email via Gmail.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body (plain text)
        from_email: Sender email (optional, uses authenticated account)

    Returns:
        Success status and message ID
    """
    # TODO: Implement with Gmail API when credentials are set up
    return {
        "success": True,
        "message_id": "mock_message_id_123",
        "to": to,
        "subject": subject,
        "note": "Mock email sent - configure Gmail API for production",
        "preview": f"To: {to}\nSubject: {subject}\n\n{body[:100]}..."
    }


@tool(show_result=True)
def check_email_deliverability(email: str) -> Dict[str, bool]:
    """
    Basic email validation and format checking.

    Args:
        email: Email address to validate

    Returns:
        Validation results
    """
    # Basic regex for email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    is_valid = bool(re.match(email_pattern, email))

    return {
        "valid": is_valid,
        "format_correct": is_valid,
        "email": email,
        "note": "Basic format validation - enhance with SMTP check for production"
    }


# Production implementation (commented out - requires setup):
"""
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def get_gmail_service():
    creds = Credentials.from_authorized_user_file('token.json',
        ['https://www.googleapis.com/auth/gmail.send',
         'https://www.googleapis.com/auth/gmail.readonly'])
    return build('gmail', 'v1', credentials=creds)

# Uncomment and modify above functions to use Gmail API when ready
"""
