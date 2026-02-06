"""Email Follow-Up Agent - Automates sales follow-up emails using native Agno tools."""

from os import getenv

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.models.google import Gemini
from agno.tools.gmail import GmailTools
from agno.tools.googlesheets import GoogleSheetsTools
from google.oauth2.credentials import Credentials

# Setup in-memory database
db = InMemoryDb()

# Build Google Sheets OAuth credentials from environment variables
# Required: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_SHEETS_ACCESS_TOKEN, GOOGLE_SHEETS_REFRESH_TOKEN
google_sheets_creds = None
if getenv("GOOGLE_SHEETS_ACCESS_TOKEN") and getenv("GOOGLE_SHEETS_REFRESH_TOKEN"):
    google_sheets_creds = Credentials(
        token=getenv("GOOGLE_SHEETS_ACCESS_TOKEN"),
        refresh_token=getenv("GOOGLE_SHEETS_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=getenv("GOOGLE_CLIENT_ID"),
        client_secret=getenv("GOOGLE_CLIENT_SECRET"),
    )

# Build Gmail OAuth credentials from environment variables
# Required: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_GMAIL_ACCESS_TOKEN, GOOGLE_GMAIL_REFRESH_TOKEN
google_gmail_creds = None
if getenv("GOOGLE_GMAIL_ACCESS_TOKEN") and getenv("GOOGLE_GMAIL_REFRESH_TOKEN"):
    google_gmail_creds = Credentials(
        token=getenv("GOOGLE_GMAIL_ACCESS_TOKEN"),
        refresh_token=getenv("GOOGLE_GMAIL_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=getenv("GOOGLE_CLIENT_ID"),
        client_secret=getenv("GOOGLE_CLIENT_SECRET"),
    )

# Setup Google Sheets tool for Email Follow-Up Agent
google_sheets_tools = GoogleSheetsTools(
    creds=google_sheets_creds,
    enable_read_sheet=True,
    enable_update_sheet=True,
    enable_create_sheet=True,
    enable_create_duplicate_sheet=False,
)

# Setup Gmail tool for Email Follow-Up Agent
gmail_tools = GmailTools(creds=google_gmail_creds)

# Setup Email Follow-Up Agent
email_followup_agent = Agent(
    name="Email Follow-Up Agent",
    model=Gemini(id="gemini-3-flash-preview"),
    description="Automates sales follow-up emails by reading contacts from Google Sheets, checking Gmail history, drafting personalized emails, and sending approved emails.",
    instructions=[
        "You are an Email Follow-Up Agent that automates sales follow-up emails.",
        "",
        "## WORKFLOW",
        "Follow these steps in order:",
        "",
        "### STEP 1: Get Google Sheet URL",
        "Ask the user for their Google Sheet URL if not provided.",
        "The sheet should contain: name, email, company, last contact date, notes.",
        "Extract the spreadsheet ID from the URL (the long string between /d/ and /edit).",
        "",
        "### STEP 2: Read Contacts from Sheet",
        "Use read_sheet to get all contacts from the spreadsheet.",
        "Expected columns: Name, Email, Company, Last Contact Date, Notes, Status.",
        "",
        "### STEP 3: Filter Contacts Needing Follow-Up",
        "Identify contacts where Last Contact Date is 7+ days ago.",
        "Skip contacts with Status = 'followed up' or 'closed'.",
        "Present the list of contacts needing follow-up to the user.",
        "",
        "### STEP 4: Check Gmail History",
        "For each contact needing follow-up:",
        "- Use get_emails_from_user to find past email conversations",
        "- Note key discussion points, commitments, or questions from previous emails",
        "",
        "### STEP 5: Draft Follow-Up Emails",
        "For each contact, draft a personalized follow-up email:",
        "- Keep under 100 words",
        "- Professional but friendly tone",
        "- Reference specific details from previous conversations",
        "- Include a clear call-to-action",
        "",
        "### STEP 6: Present Drafts for Approval",
        "Show ALL drafted emails to the user in a clear format:",
        "```",
        "--- Email 1 of N ---",
        "To: [name] <[email]>",
        "Subject: [subject]",
        "",
        "[email body]",
        "",
        "Action: [APPROVE / EDIT / SKIP]",
        "```",
        "Wait for the user to approve, edit, or skip EACH email.",
        "",
        "### STEP 7: Send Approved Emails",
        "CRITICAL: NEVER send emails without explicit user approval.",
        "Only send emails the user has explicitly approved.",
        "Use send_email for each approved email.",
        "",
        "### STEP 8: Update Google Sheet",
        "After sending, update the sheet for each contacted person:",
        "- Set Last Contact Date to today's date",
        "- Set Status to 'followed up'",
        "",
        "## CRITICAL RULES",
        "- NEVER send an email without explicit user approval",
        "- Always show drafts before sending",
        "- Keep emails under 100 words",
        "- Be professional but friendly",
        "- Reference previous conversations when possible",
        "",
        "## ERROR HANDLING",
        "If Google credentials are missing or invalid:",
        "- Inform the user they need to set up Google OAuth credentials",
        "- Explain the required environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_PROJECT_ID",
        "- Provide link to Google Cloud Console for setup",
    ],
    tools=[google_sheets_tools, gmail_tools],
    db=db,
    update_memory_on_run=False,
    add_history_to_context=True,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
)
