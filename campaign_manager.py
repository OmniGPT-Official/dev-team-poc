"""
Campaign Manager - Pattern 1: Single Agent with Internal Workflow

A unified agent interface for outbound calling campaigns. User talks to ONE agent
that internally orchestrates a multi-step workflow using specialized agents.

Architecture: Single Agent + WorkflowTools
- User interacts with: Campaign Manager (single agent)
- Internal workflow: Read leads → Batch call → Log results
- Workflow equipped as tool via WorkflowTools
- Conversational interface with step-by-step orchestration
"""

from agno.agent import Agent
from agno.workflow import Workflow, Step
from agno.tools.workflow import WorkflowTools
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
# Internal Workflow: Outbound Calling Process
# ─────────────────────────────────────────────────────────────────────────

_outbound_calling_workflow = Workflow(
    name="Outbound Calling Workflow",
    description="""
    Multi-step workflow for outbound calling campaigns:
    1. Read and filter leads from Google Sheets
    2. Submit batch calls to ElevenLabs
    3. Update Google Sheets with call results
    """,
    steps=[
        Step(
            name="Step 1: Read Leads",
            agent=lead_reader_agent,
            description="""
            **STEP 1 of 3: Read and Filter Leads**

            Your task:
            1. Get Google Sheet URL from user (if not already provided)
            2. Use read_sheet to fetch all leads
            3. Filter for leads ready to call (status empty or 'not_contacted')
            4. Validate phone numbers are in E.164 format
            5. Report: total leads, ready to call, skipped

            **STOP HERE** - Pass the filtered lead list to Step 2
            End with: "Step 1 complete. Ready for Step 2: Batch Calling."
            """,
        ),
        Step(
            name="Step 2: Submit Batch Call",
            agent=calling_coordinator_agent,
            description="""
            **STEP 2 of 3: Submit and Monitor Batch Call**

            Your task:
            1. Take the filtered leads from Step 1
            2. Format recipients for ElevenLabs: [{phone_number, restaurant_name, city, country}]
            3. Submit batch call using submit_batch_call
            4. Monitor batch status with get_batch_status
            5. Wait for calls to complete
            6. Collect call results

            **STOP HERE** - Pass call results to Step 3
            End with: "Step 2 complete. Ready for Step 3: Logging Results."
            """,
        ),
        Step(
            name="Step 3: Log Results",
            agent=results_logger_agent,
            description="""
            **STEP 3 of 3: Update Google Sheets**

            Your task:
            1. Take call results from Step 2
            2. For each lead, update Google Sheet:
               - Status: 'interested', 'not_interested', 'no_answer', etc.
               - Call_Attempts: increment by 1
               - Notes: what happened on the call
            3. Use update_sheet in batch mode
            4. Report: updated count, outcomes summary

            **WORKFLOW COMPLETE**
            End with: "✓ Campaign complete! All results logged to Google Sheet."
            """,
        ),
    ],
)


# ─────────────────────────────────────────────────────────────────────────
# WorkflowTools: Equip workflow as tool to agent
# ─────────────────────────────────────────────────────────────────────────

workflow_tools = WorkflowTools(
    workflow=_outbound_calling_workflow,
    enable_run_workflow=True,  # Enable workflow execution
    enable_think=False,  # Don't need internal thinking scratchpad
    enable_analyze=False,  # Don't need result analysis (agent handles this)
)


# ─────────────────────────────────────────────────────────────────────────
# Campaign Manager - Single Agent with Workflow Tool
# ─────────────────────────────────────────────────────────────────────────

campaign_manager = Agent(
    name="Campaign Manager",
    model=MODEL,
    description="Manages outbound calling campaigns from start to finish using Google Sheets and ElevenLabs",
    instructions=[
        "You are the Campaign Manager - a single agent interface for outbound calling campaigns.",
        "",
        "## YOUR ROLE",
        "You orchestrate the entire campaign workflow conversationally.",
        "The user talks to YOU, and you coordinate everything behind the scenes.",
        "",
        "## CONVERSATIONAL START",
        "When user greets you or wants to run a campaign:",
        "1. Greet them warmly",
        "2. Explain: 'I help run outbound calling campaigns using ElevenLabs and Google Sheets'",
        "3. Ask: 'Please share your Google Sheet URL with the leads you want to call'",
        "",
        "## REQUIRED INFORMATION",
        "You need:",
        "- Google Sheet URL with leads",
        "- (Optional) Campaign name",
        "",
        "The sheet should have columns:",
        "- phone_number (E.164 format: +12025551234)",
        "- restaurant_name or name",
        "- city, country",
        "- status (you'll update this)",
        "",
        "## RUNNING THE CAMPAIGN",
        "Once you have the sheet URL:",
        "1. Use the 'Outbound Calling Workflow' tool to execute the campaign",
        "2. The workflow will:",
        "   - Read and filter leads (Step 1)",
        "   - Submit batch calls (Step 2)",
        "   - Update results in sheet (Step 3)",
        "3. Keep user informed of progress at each step",
        "",
        "## PROGRESS UPDATES",
        "Communicate clearly:",
        "- 'Reading leads from your sheet...'",
        "- 'Submitting batch call to ElevenLabs...'",
        "- 'Campaign in progress: X/Y calls completed'",
        "- 'Updating Google Sheet with results...'",
        "",
        "## ERROR HANDLING",
        "",
        "**No Google Sheets credentials:**",
        "- Tell user: 'Please connect your Google account in Settings → Integrations'",
        "- Explain: 'I need Google Sheets access to read and update your leads'",
        "",
        "**Invalid phone numbers:**",
        "- Report: 'Skipped X leads with invalid phone numbers'",
        "- Proceed with valid leads only",
        "",
        "**ElevenLabs API error:**",
        "- Check error message from workflow",
        "- Common issues:",
        "  - Missing API key: 'ELEVENLABS_API_KEY not set'",
        "  - Invalid agent ID: 'ELEVENLABS_AGENT_ID not found'",
        "  - Network error: Report and suggest retry",
        "",
        "## FINAL REPORT",
        "After campaign completes, provide:",
        "- Total leads processed",
        "- Interested: count and details",
        "- Not interested: count",
        "- No answer: count",
        "- All results logged to Google Sheet",
        "- Next steps",
        "",
        "## COMMUNICATION STYLE",
        "- Be conversational and friendly",
        "- Use emojis for visual progress: 📊 📞 ✓ ⚠️",
        "- Report progress at each major step",
        "- Celebrate success: 'Campaign complete! 🎉'",
        "- Be helpful and professional",
    ],
    tools=[workflow_tools],  # Workflow equipped as tool via WorkflowTools
    pre_hooks=[inject_user_tools],  # Inject Google Sheets tools via OAuth
    db=db,
    update_memory_on_run=True,  # Remember Sheet URLs and campaign details
    add_history_to_context=True,  # Main agent needs context for conversation
    num_history_messages=10,  # FIX: Limit history to last 10 messages as safety measure
    add_datetime_to_context=True,
    markdown=True,
)
