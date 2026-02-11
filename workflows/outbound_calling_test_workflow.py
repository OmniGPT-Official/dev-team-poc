"""
Outbound Calling Test Workflow - Simple OAuth Version

Minimal workflow for testing first iteration:
1. Read Google Sheet with OAuth (real data)
2. Submit batch call to ElevenLabs

This workflow uses OAuth-enabled tools to access real Google Sheets data.
"""

from agno.agent import Agent
from agno.workflow import Workflow, Step
from agno.models.google import Gemini
from services.tool_injector import make_tool_hook
from tools.elevenlabs_tools import submit_batch_call, get_batch_status
from db import db

# Cost-effective model for testing
MODEL = Gemini(id="gemini-3-flash-preview")


# ─────────────────────────────────────────────────────────────────────────
# Test Agent: Calling Test Coordinator
# ─────────────────────────────────────────────────────────────────────────

calling_test_agent = Agent(
    name="Calling Test Coordinator",
    model=MODEL,
    description="Simple agent for testing outbound calling first iteration",
    instructions=[
        "You help test the outbound calling workflow step by step",
        "",
        "**STEP 1: Get Google Sheet**",
        "1. Ask user: 'Please share your Google Sheet URL for the leads'",
        "2. Use read_sheet tool to fetch the data",
        "3. Show user the leads you found (restaurant_name, phone_number, city)",
        "4. Count total leads and leads with valid phone numbers",
        "5. Ask: 'I found X leads. Ready to submit batch call to ElevenLabs?'",
        "",
        "**STEP 2: Submit Batch Call**",
        "6. If user confirms, use submit_batch_call with the leads",
        "7. Format leads as: [{phone_number, restaurant_name, city, country}]",
        "8. Use campaign name like 'Test Campaign - [Date]'",
        "9. Report the batch_id returned by ElevenLabs",
        "10. Use get_batch_status to check progress",
        "",
        "**IMPORTANT:**",
        "- Phone numbers MUST be in E.164 format (+1234567890)",
        "- If phone format is wrong, explain to user and stop",
        "- Always show user what you're doing before doing it",
        "- Be conversational and clear with status updates",
    ],
    tools=[submit_batch_call, get_batch_status],  # Static tools; Google Sheets injected via pre_hook
    pre_hooks=[make_tool_hook("google_sheets")],
    db=db,
)


# ─────────────────────────────────────────────────────────────────────────
# Workflow: Outbound Calling First Iteration Test
# ─────────────────────────────────────────────────────────────────────────

outbound_calling_test_workflow = Workflow(
    name="Outbound Calling Test",
    description="""
    Simple test workflow for outbound calling first iteration.

    **What it does:**
    1. Asks for your Google Sheet URL
    2. Reads the leads using OAuth (real data, not mock)
    3. Shows you the leads found
    4. Submits batch call to ElevenLabs
    5. Reports batch_id for tracking

    **Required:**
    - Google Sheet with columns: phone_number, restaurant_name, city, country
    - Phone numbers in E.164 format (+1234567890)
    - ELEVENLABS_API_KEY in environment
    - ELEVENLABS_AGENT_ID in environment
    - ELEVENLABS_PHONE_NUMBER_ID in environment
    - Google OAuth credentials configured

    **Testing just the first iteration:**
    - Read Google Sheet ✅
    - Submit batch to ElevenLabs ✅
    - (Retry logic, results logging - later iterations)
    """,
    steps=[
        Step(
            name="Test Calling Setup",
            agent=calling_test_agent,
            description="""
            Test the first iteration of outbound calling.

            Your tasks:
            1. Ask user for Google Sheet URL
            2. Read the sheet with OAuth (real data)
            3. Show user the leads found
            4. Ask for confirmation
            5. Submit batch call to ElevenLabs
            6. Report batch_id and status

            Be conversational and clear. Walk user through each step.
            """,
        ),
    ],
)
