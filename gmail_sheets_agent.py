"""Gmail & Google Sheets Agent - Basic agent with Gmail and Google Sheets tools using per-user OAuth credentials."""

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.gmail import GmailTools
from agno.tools.googlesheets import GoogleSheetsTools

from services.oauth_store import get_google_credentials

from db import db


def inject_oauth_tools(agent: Agent, user_id: str) -> None:
    """Pre-hook: fetch per-user Google credentials and inject tools before each run."""
    print(f"[pre-hook] inject_oauth_tools called — user_id={user_id!r}")
    if not user_id:
        print("[pre-hook] No user_id, skipping tool injection")
        return

    tools = []
    sheets_creds = get_google_credentials(user_id, "google_sheets")
    if sheets_creds:
        tools.append(
            GoogleSheetsTools(
                creds=sheets_creds,
                enable_read_sheet=True,
                enable_update_sheet=True,
                enable_create_sheet=True,
                enable_create_duplicate_sheet=False,
            )
        )

    gmail_creds = get_google_credentials(user_id, "google_gmail")
    if gmail_creds:
        tools.append(GmailTools(creds=gmail_creds))

    print(f"[pre-hook] Injecting {len(tools)} tool(s): {[type(t).__name__ for t in tools]}")
    agent.set_tools(tools)


# Setup Gmail & Google Sheets Agent
gmail_sheets_agent = Agent(
    name="Gmail & Sheets Agent",
    model=Claude(id="claude-sonnet-4-5-20250929"),
    description="A general-purpose assistant with access to Gmail and Google Sheets. Can read/send emails and read/update/create spreadsheets.",
    instructions=[
        "You are a helpful assistant with access to Gmail and Google Sheets.",
        "",
        "## CAPABILITIES",
        "- **Gmail**: Read, search, and send emails",
        "- **Google Sheets**: Read, update, and create spreadsheets",
        "",
        "## GUIDELINES",
        "- When the user asks to send an email, always draft it first and ask for approval before sending.",
        "- When reading a Google Sheet, extract the spreadsheet ID from the URL (the long string between /d/ and /edit).",
        "- Be concise and helpful in your responses.",
        "",
        "## ERROR HANDLING",
        "If Google credentials are missing or invalid:",
        "- Inform the user they need to connect their Google account in Settings",
        "- Explain that Google Sheets and Gmail access are required for this agent",
    ],
    pre_hooks=[inject_oauth_tools],
    db=db,
    update_memory_on_run=False,
    add_history_to_context=True,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
)
