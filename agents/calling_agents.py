"""
Outbound Calling Agents

Agents for managing the outbound calling workflow via ElevenLabs.
These agents coordinate to read leads, make calls, retry failures, and log results.

Uses OAuth-based Google Sheets access (like email_followup agent).
Uses custom ElevenLabsBatchCallingTools toolkit for API access.
"""

from agno.agent import Agent
from agno.models.moonshot import MoonShot
from tools.elevenlabs_batch_calling import ElevenLabsBatchCallingTools
from services.tool_injector import make_tool_hook
from db import db

# Use Gemini 3 Flash Preview for cost-effective POC testing
# Cost: ~$0.19 per million tokens vs ~$9 for Claude Sonnet 4.5
MODEL = MoonShot(id="kimi-k2.5", extra_body={"thinking": {"type": "disabled"}})


# Lead Reader Agent - Reads and filters leads from Google Sheets
lead_reader_agent = Agent(
    name="Lead Reader",
    model=MODEL,
    description="Reads leads from Google Sheets and identifies which ones to call",
    instructions=[
        "You read leads from Google Sheets for outbound calling campaigns",
        "",
        "## HOW TO USE GOOGLE SHEETS TOOL",
        "1. Extract the spreadsheet ID from the Sheet URL in your input (between /d/ and /edit)",
        "2. Use read_sheet tool with the spreadsheet ID",
        "3. The sheet should have columns: phone_number, restaurant_name (or name), city, country, email, website, status",
        "",
        "## FILTERING LOGIC",
        "You identify which leads need to be called based on their status:",
        "- If status column is empty or 'not_contacted': INCLUDE in call list",
        "- If status is 'called', 'interested', 'not_interested': SKIP them",
        "",
        "## PHONE VALIDATION",
        "Always validate phone numbers are in E.164 format (+[country code][number])",
        "Examples: +12025551234 (US), +442071234567 (UK), +34912345678 (Spain)",
        "If phone number is missing or invalid, SKIP that lead",
        "",
        "## OUTPUT FORMAT",
        "Your final response MUST be ONLY this compact structure — no raw data, no extra prose:",
        "SUMMARY: X total, Y ready, Z skipped",
        "Then a JSON array on a single line containing ONLY:",
        "  - phone_number (always required)",
        "  - The DYNAMIC_FIELDS the user specified (e.g. restaurant_name — whatever they chose)",
        "Do NOT include any other columns.",
        "Do NOT add explanations after the JSON.",
        "",
        "## ERROR HANDLING",
        "If read_sheet or update_sheet tools are not available, or Google Sheets access fails:",
        "- Tell user exactly: 'I don't have Google Sheets access. To fix this, either:'",
        "- Option 1: Set GOOGLE_OAUTH_REFRESH_TOKEN in your Railway environment variables",
        "- Option 2: Connect Google Sheets in AgentOS Settings → Integrations → Google Sheets",
        "- Important: google_sheets and google_docs are separate connections — connecting one does not connect the other"
    ],
    tools=[],  # Tools injected via pre_hook
    pre_hooks=[make_tool_hook("google_sheets")],
    db=db,
    add_history_to_context=False,  # FIX: Disable history to prevent context overflow in workflows
    markdown=True,
)


# Calling Coordinator Agent - Manages ElevenLabs batch calling
calling_coordinator_agent = Agent(
    name="Calling Coordinator",
    model=MODEL,
    description="Coordinates batch calling via ElevenLabs and handles retries",
    instructions=[
        "You manage the outbound calling campaign using ElevenLabs",
        "",
        "## SUBMITTING BATCH CALLS",
        "When you receive the lead list from Step 1, pass every field from every lead dict directly to submit_batch_call — exactly as received.",
        "Do NOT add, remove, or rename any fields. Do NOT hardcode field names.",
        "The campaign manager controls which fields are included; your job is to pass them through unchanged.",
        "The submit_batch_call tool handles all API formatting — you just pass the full dicts.",
        "Example: if Step 1 outputs [{\"phone_number\":\"+66...\",\"restaurant_name\":\"Pad Thai\"}], pass that exact list as recipients.",
        "",
        "You submit batch calls with properly formatted recipient lists",
        "You monitor batch status and wait for calls to complete",
        "You handle retries for failed/unanswered calls (up to 3 attempts total)",
        "You track which calls succeeded, failed, or need retry",
        "For each batch, you provide clear status updates",
        "When submitting batch calls, use descriptive campaign names like 'US Restaurants Feb 2026'",
        "Monitor batch status every 30 seconds until complete",
        "If calls fail, wait 2 minutes before retrying",
        "After 3 total attempts, mark as 'no_answer_3x' for email follow-up",
        "Always report: total calls, successful, failed, pending retry",
        "Keep the user informed of progress throughout the campaign"
    ],
    tools=[ElevenLabsBatchCallingTools()],  # Use custom toolkit for batch calling
    db=db,
    add_history_to_context=False,  # No history — each step runs fresh
    num_history_messages=0,  # FIX: 0 prevents DB history loading; 5 was still loading into context
    markdown=True,
)


# Results Logger Agent - Updates Google Sheets with call outcomes
results_logger_agent = Agent(
    name="Results Logger",
    model=MODEL,
    description="Updates Google Sheets with call results and outcomes",
    instructions=[
        "You update the Google Sheet with results from each call",
        "",
        "## HOW TO UPDATE SHEETS",
        "1. Use update_sheet tool with spreadsheet ID",
        "2. Specify row number to update (1-indexed, row 1 = header)",
        "3. Provide updates as dictionary: {'Status': 'interested', 'Notes': 'text'}",
        "",
        "## OUTCOME VALUES",
        "Log the outcome:",
        "- 'interested': Lead showed interest",
        "- 'not_interested': Lead declined",
        "- 'no_answer': First/second attempt, no answer",
        "- 'no_answer_3x': Third attempt failed, mark for email follow-up",
        "- 'calling': Call in progress",
        "",
        "## WHAT TO LOG",
        "- Status column: outcome value",
        "- Call_Attempts column: increment by 1",
        "- Notes column: what happened on the call",
        "- For interested leads: note what they're interested in",
        "- For not interested: note reason if provided",
        "",
        "## ERROR HANDLING",
        "If Google Sheets update fails:",
        "- Inform user credentials may have expired",
        "- Tell them to reconnect Google account in Settings"
    ],
    tools=[],  # Tools injected via pre_hook
    pre_hooks=[make_tool_hook("google_sheets")],
    db=db,
    add_history_to_context=False,  # FIX: Disable history to prevent context overflow in workflows
    markdown=True,
)

