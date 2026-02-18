"""
Outbound Calling Agents

Agents for managing the outbound calling workflow via ElevenLabs.
These agents coordinate to read leads, make calls, retry failures, and log results.

Uses OAuth-based Google Sheets access (like email_followup agent).
Uses custom ElevenLabsBatchCallingTools toolkit for API access.
"""

from agno.agent import Agent
from agno.models.google import Gemini
from tools.elevenlabs_batch_calling import ElevenLabsBatchCallingTools
from services.tool_injector import make_tool_hook
from db import db

# Use Gemini 3 Flash Preview for cost-effective POC testing
# Cost: ~$0.19 per million tokens vs ~$9 for Claude Sonnet 4.5
MODEL = Gemini(id="gemini-3-flash-preview")


# Lead Reader Agent - Reads and filters leads from Google Sheets
lead_reader_agent = Agent(
    name="Lead Reader",
    model=MODEL,
    description="Reads leads from Google Sheets and identifies which ones to call",
    instructions=[
        "You read leads from Google Sheets for outbound calling campaigns",
        "",
        "## HOW TO USE GOOGLE SHEETS TOOL",
        "1. Ask user for their Google Sheet URL if not provided",
        "2. Extract spreadsheet ID from URL (between /d/ and /edit)",
        "3. Use read_sheet tool with the spreadsheet ID",
        "4. The sheet should have columns: phone_number, restaurant_name (or name), city, country, email, website, status",
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
        "Provide:",
        "- Total leads found in sheet",
        "- Leads ready to call (count)",
        "- Leads skipped (count and reasons)",
        "- List each ready lead as: {phone_number, restaurant_name, city, country, email, website}",
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
    num_history_messages=5,  # FIX: Limit to last 5 messages as safety measure
    markdown=True,
)


# Calling Coordinator Agent - Manages ElevenLabs batch calling
calling_coordinator_agent = Agent(
    name="Calling Coordinator",
    model=MODEL,
    description="Coordinates batch calling via ElevenLabs and handles retries",
    instructions=[
        "You manage the outbound calling campaign using ElevenLabs",
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
    add_history_to_context=False,  # FIX: Disable history to prevent context overflow in workflows
    num_history_messages=5,  # FIX: Limit to last 5 messages as safety measure
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
    num_history_messages=5,  # FIX: Limit to last 5 messages as safety measure
    markdown=True,
)


# Campaign Coordinator Agent - Orchestrates the overall workflow
campaign_coordinator_agent = Agent(
    name="Campaign Coordinator",
    model=MODEL,
    description="Orchestrates the entire outbound calling campaign workflow",
    instructions=[
        "You coordinate outbound calling campaigns from start to finish",
        "",
        "## CONVERSATIONAL START",
        "If the user greets you or doesn't provide details yet:",
        "- Greet them warmly",
        "- Explain what you do: 'I help run outbound calling campaigns using ElevenLabs'",
        "- Ask for: Google Sheet URL with leads to call",
        "- Example: 'Please share your Google Sheet URL with the leads you want to call'",
        "",
        "## REQUIRED INFORMATION",
        "You need from the user:",
        "1. Google Sheet URL containing leads",
        "2. (Optional) Campaign name (default: 'Outbound Campaign [date]')",
        "",
        "The sheet should have columns:",
        "- phone_number (E.164 format: +12025551234)",
        "- restaurant_name or name",
        "- city, country (optional)",
        "- email, website (optional)",
        "- status (you'll update this)",
        "",
        "## WORKFLOW STEPS",
        "Once you have the sheet URL:",
        "",
        "1. READ LEADS: Use read_sheet to get all leads from Google Sheet",
        "2. FILTER: Identify leads ready to call (status empty or 'not_contacted')",
        "3. VALIDATE: Check phone numbers are in E.164 format",
        "4. CONFIRM: Show user list of leads to call, ask for approval",
        "5. CALL: Submit batch to ElevenLabs using submit_batch_call",
        "6. MONITOR: Check batch status until complete",
        "7. RESULTS: Update sheet with outcomes using update_sheet",
        "8. RETRY: Retry failed calls (up to 3 attempts total)",
        "9. REPORT: Provide final summary",
        "",
        "## PROGRESS UPDATES",
        "Keep user informed:",
        "- 'Reading 50 leads from your sheet...'",
        "- 'Calling 30 restaurants now...'",
        "- 'Batch in progress: 15/30 calls completed'",
        "",
        "## FINAL REPORT",
        "Include:",
        "- Total leads processed",
        "- Interested: count and details",
        "- Not interested: count",
        "- No answer (need retry): count",
        "- Need email follow-up: count",
        "- Next steps",
        "",
        "## ERROR HANDLING",
        "If read_sheet or update_sheet tools are not available, or Google Sheets access fails:",
        "- Tell user exactly: 'I don't have Google Sheets access. To fix this, either:'",
        "- Option 1: Set GOOGLE_OAUTH_REFRESH_TOKEN in your Railway environment variables",
        "- Option 2: Connect Google Sheets in AgentOS Settings → Integrations → Google Sheets",
        "- Important: google_sheets and google_docs are separate — connecting one does not connect the other",
        "",
        "",
        "If ElevenLabs fails:",
        "- Check ELEVENLABS_API_KEY is set",
        "- Provide clear error message",
        "",
        "You are friendly, professional, and results-oriented"
    ],
    tools=[ElevenLabsBatchCallingTools()],  # Use custom toolkit for batch calling
    # Google Sheets tools injected via pre_hook
    pre_hooks=[make_tool_hook("google_sheets")],
    db=db,
    add_history_to_context=True,  # Orchestrator needs context for conversation
    num_history_messages=10,  # FIX: Limit history to prevent 1M+ token overflow
    add_datetime_to_context=True,
    markdown=True,
)
