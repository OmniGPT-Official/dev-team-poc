"""
Outbound Calling Agents

Agents for managing the outbound calling workflow via ElevenLabs.
These agents coordinate to read leads, make calls, retry failures, and log results.
"""

from agno.agent import Agent
from agno.models.google import Gemini
from tools.google_sheets_tools import (
    read_google_sheet,
    update_sheet_row,
    find_contacts_needing_followup
)
from tools.elevenlabs_tools import (
    submit_batch_call,
    get_batch_status,
    retry_failed_calls,
    get_call_result
)

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
        "You identify which leads need to be called based on their status",
        "You format leads for batch calling (phone_number, restaurant_name, city, etc.)",
        "You filter out leads that have already been called or are marked as do-not-call",
        "You provide a clean list of recipients ready for calling",
        "Format each lead as: {phone_number, restaurant_name, city, country, email, website}",
        "Always validate phone numbers are in E.164 format (+[country code][number])",
        "If status column is empty or 'not_contacted', include in call list",
        "If status is 'called', 'interested', 'not_interested', skip them",
        "Provide clear count of total leads and leads ready to call"
    ],
    tools=[
        read_google_sheet,
        find_contacts_needing_followup
    ]
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
    tools=[
        submit_batch_call,
        get_batch_status,
        retry_failed_calls,
        get_call_result
    ]
)


# Results Logger Agent - Updates Google Sheets with call outcomes
results_logger_agent = Agent(
    name="Results Logger",
    model=MODEL,
    description="Updates Google Sheets with call results and outcomes",
    instructions=[
        "You update the Google Sheet with results from each call",
        "You log the outcome: interested, not_interested, no_answer, no_answer_3x",
        "You track number of call attempts for each lead",
        "You add notes about what happened on the call",
        "You update the status column to reflect current state",
        "Status values: 'calling', 'interested', 'not_interested', 'no_answer', 'no_answer_3x'",
        "For interested leads: add notes about what they're interested in",
        "For not interested: add reason if provided",
        "For no_answer_3x: mark for email follow-up",
        "Always update the sheet immediately after getting call results",
        "Provide confirmation of each row updated",
        "Keep data clean and consistent"
    ],
    tools=[
        update_sheet_row,
        read_google_sheet
    ]
)


# Campaign Coordinator Agent - Orchestrates the overall workflow
campaign_coordinator_agent = Agent(
    name="Campaign Coordinator",
    model=MODEL,
    description="Orchestrates the entire outbound calling campaign workflow",
    instructions=[
        "You coordinate the entire outbound calling campaign from start to finish",
        "You work with the Lead Reader, Calling Coordinator, and Results Logger",
        "Your workflow:",
        "",
        "1. START: Get campaign details from user (sheet URL, campaign name)",
        "2. LEADS: Ask Lead Reader to identify leads ready to call",
        "3. VALIDATE: Check we have valid leads with phone numbers",
        "4. CALL: Ask Calling Coordinator to submit batch and monitor",
        "5. RESULTS: Ask Results Logger to update sheet with outcomes",
        "6. RETRY: If failures, coordinate retry (up to 3 attempts)",
        "7. REPORT: Provide final campaign summary",
        "",
        "You communicate clearly with the user at each step",
        "You provide progress updates: 'Calling 50 restaurants...'",
        "You handle errors gracefully and explain what happened",
        "You identify leads needing email follow-up (no_answer_3x)",
        "Your final report includes:",
        "  - Total leads processed",
        "  - Interested: count and details",
        "  - Not interested: count",
        "  - Need email follow-up: count",
        "  - Next steps for the user",
        "You are professional, efficient, and results-oriented"
    ],
    tools=[
        read_google_sheet,
        update_sheet_row,
        submit_batch_call,
        get_batch_status,
        retry_failed_calls
    ]
)
