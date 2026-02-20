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
from agno.models.moonshot import MoonShot
from agents.calling_agents import (
    lead_reader_agent,
    calling_coordinator_agent,
    results_logger_agent,
)
from services.tool_injector import inject_user_tools
from db import db

# Cost-effective model for POC
MODEL = MoonShot(id="kimi-k2.5", extra_body={"thinking": {"type": "disabled"}})


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

FIRST — check your input for pre-provided lead data:
- If your input contains 'LEADS_ALREADY_READ: [...]' → parse and use that JSON directly. Skip read_sheet entirely.
- If no LEADS_ALREADY_READ in input → read the sheet using read_sheet tool with the Sheet URL from your input.

Your task (whichever path):
1. Use lead data (from input or read_sheet)
2. Filter for leads ready to call (status empty or 'not_contacted')
3. Validate phone numbers are in E.164 format
4. Output ONLY: one summary line + compact JSON array of ready leads

**CRITICAL - Keep output small. Step 2 receives your full response as context.**
Output format (nothing else after the JSON):
SUMMARY: X total, Y ready, Z skipped
JSON array with ONLY phone_number + the DYNAMIC_FIELDS specified by the user.
Example (if user chose restaurant_name): [{"phone_number":"+66...","restaurant_name":"..."},...]
Do NOT include any other columns — preserve the sheet; only send what ElevenLabs needs.

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
            2. Pass ALL fields from Step 1 leads to submit_batch_call — include every column (phone_number, language, restaurant_name, city, country, and any others). Do NOT hardcode or filter fields.
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
        "You need (collect in this order, one question at a time):",
        "1. Google Sheet URL with leads",
        "2. Which columns to send to ElevenLabs as dynamic variables (beyond phone_number)",
        "   - Ask: 'Which fields from your sheet should the AI agent use during the call? For example: restaurant_name, city, country. Your sheet will not be modified — only these fields are sent to ElevenLabs.'",
        "   - The user may say just one field (e.g. 'restaurant_name') or several",
        "   - Always include phone_number automatically — never ask about it",
        "   - Save the user's answer as: DYNAMIC_FIELDS = [list of field names]",
        "3. (Optional) Campaign name",
        "",
        "## RUNNING THE CAMPAIGN",
        "Once you have the sheet URL and DYNAMIC_FIELDS:",
        "1. Pass DYNAMIC_FIELDS clearly in your message when triggering the workflow",
        "   Example: 'Run campaign. Sheet: <url>. Dynamic fields for ElevenLabs: restaurant_name'",
        "2. Use the 'Outbound Calling Workflow' tool to execute the campaign",
        "2. The workflow will:",
        "   - Read and filter leads (Step 1)",
        "   - Submit batch calls (Step 2)",
        "   - Update results in sheet (Step 3)",
        "3. Keep user informed of progress at each step",
        "",
        "## CARRYING DATA INTO THE WORKFLOW",
        "When the user says 'start' or 'run campaign', you may already have the lead data from earlier in this conversation.",
        "DO NOT make Step 1 re-read the sheet if you already read it. Instead:",
        "1. Include the full lead list in your workflow trigger message",
        "2. Format: 'LEADS_ALREADY_READ: [<the JSON array you already have>]'",
        "3. Also include: SHEET_URL, DYNAMIC_FIELDS, CAMPAIGN_NAME",
        "Example trigger message:",
        "  Sheet: https://... | DYNAMIC_FIELDS: restaurant_name | LEADS_ALREADY_READ: [{\"phone_number\":\"+66...\",\"restaurant_name\":\"Pad Thai\"},...] | Campaign: Bangkok Feb 2026",
        "This prevents double reads and OAuth failures on the second request.",
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
        "## MEMORY",
        "You have agentic memory — use it to remember things that are useful ACROSS sessions.",
        "REMEMBER (call update_user_memory): Google Sheet URLs the user has used before.",
        "DO NOT REMEMBER: restaurant names, phone numbers, lead details — that data lives in the sheet.",
        "When starting a new session, check if you have a stored sheet URL and ask the user if they want to use the same sheet.",
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
    update_memory_on_run=False,  # Disable auto-summaries that pollute cross-session memory
    enable_agentic_memory=True,  # Use agentic memory for deliberate cross-session recall
    add_history_to_context=True,  # Main agent needs context for conversation
    num_history_messages=3,  # FIX: Reduced from 10 — campaign results are large, 10 caused 4MB overflow
    add_datetime_to_context=True,
    markdown=True,
)
