"""
Outbound Calling Workflow

Automated outbound calling campaign workflow for restaurants/hotels.
Reads leads from Google Sheets, calls via ElevenLabs, retries failures, logs results.
"""

from agno.workflow import Step, Steps, Workflow
from agents.calling_agents import (
    lead_reader_agent,
    calling_coordinator_agent,
    results_logger_agent,
    campaign_coordinator_agent
)


# ───────────────────────────────────────────────────────────────────────────
# STEP 1: Campaign Setup & Lead Identification
# ───────────────────────────────────────────────────────────────────────────

campaign_setup_steps = Steps(
    name="Campaign Setup",
    description="Set up campaign and identify leads to call",
    steps=[
        Step(
            name="Identify Leads",
            agent=lead_reader_agent,
            description="Read Google Sheet and identify leads ready to call",
        ),
    ],
)


# ───────────────────────────────────────────────────────────────────────────
# STEP 2: Execute Calling Campaign
# ───────────────────────────────────────────────────────────────────────────

calling_execution_steps = Steps(
    name="Execute Calls",
    description="Submit batch calls and monitor progress",
    steps=[
        Step(
            name="Submit and Monitor Batch",
            agent=calling_coordinator_agent,
            description="Submit batch call to ElevenLabs and monitor until complete",
        ),
    ],
)


# ───────────────────────────────────────────────────────────────────────────
# STEP 3: Process Results and Retry Failures
# ───────────────────────────────────────────────────────────────────────────

results_processing_steps = Steps(
    name="Process Results",
    description="Log call outcomes and retry failures",
    steps=[
        Step(
            name="Log Results to Sheet",
            agent=results_logger_agent,
            description="Update Google Sheet with call outcomes and status",
        ),
        Step(
            name="Handle Retries",
            agent=calling_coordinator_agent,
            description="Retry failed calls (up to 3 attempts total)",
        ),
    ],
)


# ───────────────────────────────────────────────────────────────────────────
# STEP 4: Final Report
# ───────────────────────────────────────────────────────────────────────────

campaign_reporting_steps = Steps(
    name="Campaign Report",
    description="Generate final campaign summary and next steps",
    steps=[
        Step(
            name="Generate Report",
            agent=campaign_coordinator_agent,
            description="Summarize campaign results and identify next actions",
        ),
    ],
)


# ───────────────────────────────────────────────────────────────────────────
# FULL WORKFLOW: Outbound Calling Campaign
# ───────────────────────────────────────────────────────────────────────────

outbound_calling_workflow = Workflow(
    name="Outbound Calling Campaign",
    description="""
    Automated outbound calling workflow for sales campaigns.

    **What it does:**
    1. Reads leads from Google Sheets
    2. Calls each lead via ElevenLabs voice agent
    3. Retries failed/unanswered calls (up to 3 attempts)
    4. Updates Google Sheet with call outcomes
    5. Identifies leads needing email follow-up

    **Required Google Sheet columns:**
    - restaurant_name (or business name)
    - phone_number (E.164 format: +1234567890)
    - city
    - country
    - email (optional, for follow-up)
    - website (optional)
    - status (auto-filled by workflow)
    - call_attempts (auto-filled)
    - call_outcome (auto-filled)
    - notes (auto-filled)

    **Required environment variables:**
    - ELEVENLABS_API_KEY
    - ELEVENLABS_AGENT_ID
    - ELEVENLABS_PHONE_NUMBER_ID
    - GOOGLE_OAUTH_CLIENT_ID (for Sheets access)
    - GOOGLE_OAUTH_CLIENT_SECRET
    - GOOGLE_OAUTH_REFRESH_TOKEN

    **Workflow steps:**
    1. Campaign Setup: Identify leads to call
    2. Execute Calls: Submit batch and monitor
    3. Process Results: Log outcomes and retry failures
    4. Campaign Report: Summary and next steps
    """,
    steps=[
        campaign_setup_steps,
        calling_execution_steps,
        results_processing_steps,
        campaign_reporting_steps,
    ],
)


# ───────────────────────────────────────────────────────────────────────────
# SIMPLE TEST WORKFLOW (for testing without full orchestration)
# ───────────────────────────────────────────────────────────────────────────

simple_calling_workflow = Workflow(
    name="Simple Calling Test",
    description="""
    Simplified calling workflow for quick testing.

    Uses only the Campaign Coordinator agent to run a basic campaign.
    Good for testing ElevenLabs integration and Google Sheets access.
    """,
    steps=[
        Step(
            name="Run Simple Campaign",
            agent=campaign_coordinator_agent,
            description="Run a basic calling campaign with all steps in one agent",
        ),
    ],
)
