"""
Google Sheets Tools for Email Follow-Up Workflow

These tools enable reading, writing, and analyzing Google Sheets
for contact management and follow-up tracking.
"""

from agno.tools import tool
from typing import List, Dict, Any
import os

# Note: This is a simplified version for testing
# For production, install: pip install gspread oauth2client
# And set up Google Sheets API credentials


@tool(show_result=True)
def read_google_sheet(sheet_url: str, worksheet_name: str = "Sheet1") -> List[Dict[str, Any]]:
    """
    Read all rows from a Google Sheet and return as list of dictionaries.

    Args:
        sheet_url: Full URL of the Google Sheet
        worksheet_name: Name of the worksheet tab (default: Sheet1)

    Returns:
        List of dictionaries where keys are column headers
    """
    # TODO: Implement with gspread when credentials are set up
    # For now, return sample data for testing
    return [
        {
            "Name": "John Smith",
            "Company": "Acme Co",
            "Email": "john@acme.com",
            "Last Contact": "2026-01-28",
            "Status": "Pending",
            "Notes": "Met at conference, interested in demo"
        },
        {
            "Name": "Sarah Lee",
            "Company": "TechCorp",
            "Email": "sarah@techcorp.com",
            "Last Contact": "2026-01-25",
            "Status": "Interested",
            "Notes": "Wants pricing information"
        }
    ]


@tool(show_result=True)
def update_sheet_row(
    sheet_url: str,
    row_number: int,
    updates: Dict[str, Any],
    worksheet_name: str = "Sheet1"
) -> Dict[str, str]:
    """
    Update specific cells in a Google Sheet row.

    Args:
        sheet_url: Full URL of the Google Sheet
        row_number: Row number to update (1-indexed, includes header)
        updates: Dictionary of {column_name: new_value}
        worksheet_name: Name of the worksheet tab

    Returns:
        Success/failure status
    """
    # TODO: Implement with gspread when credentials are set up
    return {
        "success": True,
        "message": f"Updated row {row_number} with {updates}",
        "note": "Using mock data - configure Google Sheets API for production"
    }


@tool(show_result=True)
def find_contacts_needing_followup(
    sheet_url: str,
    days_threshold: int = 7,
    worksheet_name: str = "Sheet1"
) -> List[Dict[str, Any]]:
    """
    Find contacts in Google Sheet that need follow-up based on days since last contact.

    Args:
        sheet_url: Full URL of the Google Sheet
        days_threshold: Number of days since last contact to trigger follow-up
        worksheet_name: Name of the worksheet tab

    Returns:
        List of contacts needing follow-up with their details
    """
    from datetime import datetime, timedelta

    # For testing, use mock data
    records = read_google_sheet(sheet_url, worksheet_name)

    today = datetime.now()
    threshold_date = today - timedelta(days=days_threshold)

    needs_followup = []
    for record in records:
        last_contact = record.get("Last Contact", "")
        if last_contact:
            try:
                contact_date = datetime.strptime(last_contact, "%Y-%m-%d")
                if contact_date <= threshold_date:
                    needs_followup.append(record)
            except ValueError:
                continue

    return needs_followup


# Production implementation (commented out - requires setup):
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = ['https://spreadsheets.google.com/feeds',
          'https://www.googleapis.com/auth/drive']

def get_sheets_client():
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json', SCOPES
    )
    return gspread.authorize(creds)

# Uncomment and modify above functions to use gspread when ready
"""
