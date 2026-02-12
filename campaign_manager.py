"""
Campaign Manager - Pattern 1: Single Agent + Internal Workflow

A unified interface for outbound calling campaigns that internally orchestrates
the full workflow: read leads → batch call → log results.

User talks to ONE agent (Campaign Manager), which coordinates specialized
sub-agents internally via workflow execution.

Architecture Pattern: Single Agent + Internal Workflows
- User Experience: Talk to one agent, get everything done
- Internal: Workflow coordinates lead_reader, calling_coordinator, results_logger
- Use Case: Deterministic process, hide complexity from user
"""

from agno.agent import Agent
from agno.workflow import Workflow, Step
from agno.models.google import Gemini
from agents.calling_agents import (
    lead_reader_agent,
    calling_coordinator_agent,
    results_logger_agent,
)
from services.tool_injector import inject_user_tools
from db import db

# Cost-effective model for POC
MODEL = Gemini(id="gemini-3-flash-preview")


# ─────────────────────────────────────────────────────────────────────────
# Internal Workflow (Hidden from User)
# ─────────────────────────────────────────────────────────────────────────

_outbound_calling_internal_workflow = Workflow(
    name="_outbound_calling_workflow",  # _ prefix = internal/private
    description="Internal workflow for automated outbound calling campaigns",
    steps=[
        Step(
            name="Step 1: Read Leads",
            agent=lead_reader_agent,
            description="""
            Read leads from user's Google Sheet.

            Tasks:
            1. Use read_sheet tool to fetch leads
            2. Filter for valid phone numbers (E.164 format)
            3. Return formatted leads list
            """,
        ),
        Step(
            name="Step 2: Submit Batch Call",
            agent=calling_coordinator_agent,
            description="""
            Submit batch calling job to ElevenLabs.

            Tasks:
            1. Take leads from Step 1
            2. Use submit_batch_call with proper formatting
            3. Return batch_id for tracking
            """,
        ),
        Step(
            name="Step 3: Log Results",
            agent=results_logger_agent,
            description="""
            Update Google Sheet with call results.

            Tasks:
            1. Use batch_id from Step 2
            2. Monitor batch status
            3. Update sheet with:
               - Status: 'contacted'
               - Last contact date: today's date
            """,
        ),
    ],
)


# ─────────────────────────────────────────────────────────────────────────
# Campaign Manager Agent (User Interface)
# ─────────────────────────────────────────────────────────────────────────

campaign_manager = Agent(
    name="Campaign Manager",
    model=MODEL,
    description="Manages outbound calling campaigns from start to finish using Google Sheets and ElevenLabs",
    instructions=[
        "You are the Campaign Manager - a single point of contact for outbound calling campaigns.",
        "",
        "## YOUR ROLE",
        "You coordinate the entire calling campaign process internally.",
        "User talks ONLY to you - they never interact with sub-agents.",
        "",
        "## WORKFLOW STEPS",
        "When user wants to run a campaign:",
        "",
        "### 1. Get Google Sheet URL",
        "- Ask: 'Please share your Google Sheet URL with the leads to call'",
        "- Validate the URL format",
        "- Extract spreadsheet ID",
        "",
        "### 2. Run Internal Workflow",
        "- Execute _outbound_calling_internal_workflow",
        "- The workflow will:",
        "  a) Read leads from the sheet",
        "  b) Submit batch call to ElevenLabs",
        "  c) Log results back to sheet",
        "",
        "### 3. Keep User Informed",
        "Report progress throughout:",
        "- '📊 Reading leads from your sheet...'",
        "- '✓ Found X leads (Y with valid phone numbers)'",
        "- '📞 Submitting batch call to ElevenLabs...'",
        "- '✓ Batch submitted successfully! Batch ID: batch_xyz'",
        "- '📝 Monitoring and logging results...'",
        "- '✓ Campaign complete! All results logged to your sheet'",
        "",
        "## IMPORTANT RULES",
        "- Be conversational and clear",
        "- Report progress at each major step",
        "- Handle errors gracefully with helpful messages",
        "- If OAuth credentials missing: 'Please connect your Google account in Settings'",
        "- If ElevenLabs fails: Explain the error and next steps",
        "",
        "## GOOGLE SHEET REQUIREMENTS",
        "The sheet should have these columns:",
        "- phone_number (E.164 format: +12025551234)",
        "- restaurant_name (or business name)",
        "- city",
        "- country",
        "- status (you'll update this to 'contacted')",
        "- last_contact_date (you'll update this to today's date)",
        "",
        "## ERROR HANDLING",
        "",
        "**No Google credentials:**",
        "- Tell user: 'You need to connect your Google account in Settings'",
        "- Explain: 'This allows me to read from and update your Google Sheet'",
        "",
        "**Invalid phone numbers:**",
        "- Skip leads without valid E.164 format",
        "- Report: 'Skipped X leads with invalid phone numbers'",
        "",
        "**ElevenLabs API error:**",
        "- Check if env vars are set (ELEVENLABS_API_KEY, etc.)",
        "- Provide clear error message from API",
        "",
        "## CONVERSATIONAL STYLE",
        "- Friendly and professional",
        "- Use emojis for visual progress indicators",
        "- Provide clear next steps",
        "- Celebrate successes: 'Campaign complete! 🎉'",
    ],
    tools=[_outbound_calling_internal_workflow],  # Workflow is a tool
    pre_hooks=[inject_user_tools],  # OAuth for Google Sheets
    db=db,
    update_memory_on_run=True,  # Remember Sheet URLs across sessions
    add_history_to_context=True,
    add_datetime_to_context=True,
    markdown=True,
)
