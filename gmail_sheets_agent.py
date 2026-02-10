"""Gmail & Google Sheets Agent - Basic agent with Gmail and Google Sheets tools using per-user OAuth credentials."""

from agno.agent import Agent
from agno.models.google import Gemini

from services.tool_injector import inject_user_tools

from db import db


# Setup Gmail & Google Sheets Agent
gmail_sheets_agent = Agent(
    name="Gmail & Sheets Agent",
    model=Gemini(id="gemini-3-flash-preview"),
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
    pre_hooks=[inject_user_tools],
    db=db,
    update_memory_on_run=False,
    add_history_to_context=True,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
)
