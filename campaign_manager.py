"""
Campaign Manager - Pattern 1: Single Agent with Internal Workflow

A unified agent interface for outbound calling campaigns. User talks to ONE agent
that internally orchestrates a multi-step workflow using specialized agents.

Architecture: Single Agent + WorkflowTools
- User interacts with: Campaign Manager (single agent)
- Internal workflow: Read leads → Batch call → Log results
- Workflow equipped as tool via WorkflowTools
- Conversational interface with step-by-step orchestration

Session-state caching (Bug fixes):
- Bug 1 (double-read): Leads are cached in session_state after first read. Python code
  — not LLM prompts — decides whether to re-read the sheet on subsequent runs.
- Bug 2 (cross-session memory): update_memory_on_run=False stops auto-storing run
  summaries that polluted new campaigns with old lead data.
- Bug 3 (lost intra-conversation context): session_state persists leads independently
  of num_history_messages, so the sheet read is never lost when history truncates.
- Bug 4 (LLM-instructed conditionals): The 'LEADS_ALREADY_READ' prompt workaround is
  replaced by a real Python conditional in the Step 1 executor function.
"""

import json
from typing import Optional, Dict, Any

from agno.agent import Agent
from agno.workflow import Workflow, Step
from agno.workflow.types import StepInput, StepOutput
from agno.tools.workflow import WorkflowTools
from agno.models.moonshot import MoonShot
from agno.utils.log import logger
from agents.calling_agents import (
    lead_reader_agent,
    calling_coordinator_agent,
    results_logger_agent,
)
from services.tool_injector import make_tool_hook
from db import db

# Cost-effective model for POC
MODEL = MoonShot(id="kimi-k2.5", extra_body={"thinking": {"type": "disabled"}})


# ─────────────────────────────────────────────────────────────────────────
# Workflow Step Executors: Python functions with session_state caching
#
# Each executor receives (step_input: StepInput, session_state: Dict) where
# session_state is the shared, persisted dict for this workflow session.
# Agno 2.4.8 injects session_state automatically when the function signature
# declares it — see Step._call_custom_function for the injection logic.
# ─────────────────────────────────────────────────────────────────────────


def step1_read_leads(
    step_input: StepInput,
    session_state: Optional[Dict[str, Any]] = None,
) -> StepOutput:
    """
    Step 1: Read and filter leads from Google Sheets.

    Caching: leads are stored in session_state under a key scoped to the sheet
    URL. On subsequent runs within the same session, the cached value is returned
    immediately — no OAuth call, no double-read.
    """
    if session_state is None:
        session_state = {}

    raw_input = step_input.get_input_as_string() or ""

    # ── Extract sheet URL from input for cache key ──────────────────────────
    # The campaign manager sends: "Sheet: <url>\nDYNAMIC_FIELDS: ..."
    sheet_url = ""
    for line in raw_input.splitlines():
        line = line.strip()
        if line.lower().startswith("sheet:") or line.lower().startswith("sheet url:"):
            sheet_url = line.split(":", 1)[1].strip()
            break

    if not sheet_url:
        return StepOutput(
            step_name="Step 1: Read Leads",
            content="❌ Error: No Google Sheet URL provided. Please share the sheet URL to start the campaign.",
            success=False,
        )
    leads_key = f"leads_{sheet_url}"

    # ── Inline leads: campaign manager already read the sheet ────────────────
    # The campaign manager has OAuth access and reads the sheet during conversation.
    # It passes the leads as a LEADS: line (compact JSON) so Step 1 never needs to
    # re-read the sheet (OAuth not available in executor context).
    #
    # Handles multi-line JSON: accumulates continuation lines until the array closes.
    # Uses json.loads for structural validation — substring checks accept error strings.
    # Fails loudly on invalid LEADS: line to avoid silent fallthrough to broken OAuth path.
    lines = raw_input.splitlines()
    leads_start = None
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith("leads:"):
            leads_start = i
            break

    if leads_start is not None:
        first = lines[leads_start].strip()
        inline_leads = first.split(":", 1)[1].strip()
        # Accumulate continuation lines if JSON didn't close on the same line
        if inline_leads and not inline_leads.endswith("]"):
            for continuation in lines[leads_start + 1:]:
                inline_leads += continuation.strip()
                if continuation.strip().endswith("]"):
                    break
        # Structural validation via json.loads — reject strings, error messages, wrong schema
        try:
            parsed = json.loads(inline_leads)
            if isinstance(parsed, list) and parsed and "phone_number" in parsed[0]:
                session_state[leads_key] = inline_leads
                logger.info(f"Step 1: using inline leads from campaign manager (key={leads_key})")
                return StepOutput(
                    step_name="Step 1: Read Leads",
                    content=inline_leads,
                    success=True,
                )
            else:
                logger.error(f"Step 1: LEADS line present but schema invalid: {inline_leads[:200]}")
                return StepOutput(
                    step_name="Step 1: Read Leads",
                    content="❌ Error: LEADS JSON must be a non-empty array with a phone_number field.",
                    success=False,
                )
        except json.JSONDecodeError as e:
            logger.error(f"Step 1: LEADS line is not valid JSON ({e}): {inline_leads[:200]}")
            return StepOutput(
                step_name="Step 1: Read Leads",
                content=f"❌ Error: LEADS line could not be parsed as JSON: {e}",
                success=False,
            )

    # ── Cache hit: return stored leads without re-reading the sheet ──────────
    cached_leads = session_state.get(leads_key)
    if cached_leads:
        logger.info(f"[CACHED] Using cached leads from session_state (key={leads_key})")
        return StepOutput(
            step_name="Step 1: Read Leads",
            content=cached_leads,
            success=True,
        )

    # ── Cache miss: ask lead_reader_agent to read the sheet ──────────────────
    logger.info(f"Step 1: no cached leads — reading from Google Sheet (key={leads_key})")
    result = lead_reader_agent.run(raw_input)
    output_content = result.content if result and result.content else ""

    # Only cache valid leads — never cache error messages or empty responses
    if output_content and "phone_number" in output_content:
        session_state[leads_key] = output_content
        logger.info(f"Leads cached to session_state (key={leads_key})")
    else:
        logger.warning(f"Step 1 output looks invalid — not caching: {output_content[:100]}")

    return StepOutput(
        step_name="Step 1: Read Leads",
        content=output_content,
        success=bool(output_content),
    )


def step2_submit_batch_call(
    step_input: StepInput,
    session_state: Optional[Dict[str, Any]] = None,
) -> StepOutput:
    """
    Step 2: Submit batch call to ElevenLabs using leads from Step 1.
    """
    logger.info("Step 2: starting batch call submission")
    original_input = step_input.get_input_as_string() or ""
    step1_content = step_input.get_last_step_content() or ""

    logger.info(f"Step 2: get_last_step_content length={len(step1_content)}, preview={step1_content[:120]}")

    # Fallback: if get_last_step_content() returned empty (known Agno issue with
    # executor-based steps), read leads from session_state where Step 1 cached them.
    if not step1_content or "phone_number" not in step1_content:
        if session_state:
            for key, value in session_state.items():
                if key.startswith("leads_") and value and "phone_number" in value:
                    step1_content = value
                    logger.info(f"Step 2: get_last_step_content was empty — using session_state fallback (key={key})")
                    break
        if not step1_content or "phone_number" not in step1_content:
            logger.error("Step 2: no leads available from get_last_step_content or session_state — aborting")
            return StepOutput(
                step_name="Step 2: Submit Batch Call",
                content="❌ Error: No leads received from Step 1. Cannot submit batch call.",
                success=False,
            )

    logger.info(f"Step 2: leads length={len(step1_content)}, preview={step1_content[:120]}")

    # Extract campaign name from original workflow input
    campaign_name = "Outbound Campaign"
    for line in original_input.splitlines():
        line = line.strip()
        if line.lower().startswith("campaign:") or line.lower().startswith("campaign name:"):
            campaign_name = line.split(":", 1)[1].strip()
            break

    message = (
        f"CAMPAIGN: {campaign_name}\n"
        f"LEADS (JSON array — pass exactly these fields to submit_batch_call as-is):\n{step1_content}\n"
        f"Submit batch call now."
    )

    logger.info(f"Step 2: calling calling_coordinator_agent with campaign='{campaign_name}'")
    try:
        result = calling_coordinator_agent.run(message)
        output_content = result.content if result and result.content else ""
        logger.info(f"Step 2: coordinator returned content length={len(output_content)}, preview={output_content[:120]}")
    except Exception as e:
        logger.error(f"Step 2: calling_coordinator_agent.run() raised exception: {e}")
        return StepOutput(
            step_name="Step 2: Submit Batch Call",
            content=f"❌ Error in Step 2: {e}",
            success=False,
        )

    return StepOutput(
        step_name="Step 2: Submit Batch Call",
        content=output_content,
        success=bool(output_content),
    )


def step3_log_results(
    step_input: StepInput,
    session_state: Optional[Dict[str, Any]] = None,
) -> StepOutput:
    """
    Step 3: Update Google Sheet with call outcomes from Step 2.
    """
    logger.info("Step 3: starting results logging")
    original_input = step_input.get_input_as_string() or ""
    step2_content = step_input.get_last_step_content() or ""

    logger.info(f"Step 3: step2_content length={len(step2_content)}, preview={step2_content[:120]}")

    # Extract sheet URL from original workflow input
    sheet_url = ""
    for line in original_input.splitlines():
        line = line.strip()
        if line.lower().startswith("sheet:") or line.lower().startswith("sheet url:"):
            sheet_url = line.split(":", 1)[1].strip()
            break

    logger.info(f"Step 3: sheet_url='{sheet_url}'")

    message = (
        f"Sheet URL: {sheet_url}\n"
        f"Call results from Step 2:\n{step2_content}\n"
        f"Update the Google Sheet with call outcomes."
    )

    logger.info("Step 3: calling results_logger_agent")
    try:
        result = results_logger_agent.run(message)
        output_content = result.content if result and result.content else ""
        logger.info(f"Step 3: logger returned content length={len(output_content)}, preview={output_content[:120]}")
    except Exception as e:
        logger.error(f"Step 3: results_logger_agent.run() raised exception: {e}")
        return StepOutput(
            step_name="Step 3: Log Results",
            content=f"❌ Error in Step 3: {e}",
            success=False,
        )

    return StepOutput(
        step_name="Step 3: Log Results",
        content=output_content,
        success=True,
    )


# ─────────────────────────────────────────────────────────────────────────
# Internal Workflow: Outbound Calling Process
#
# Uses callable executor steps so Python code (not LLM prompts) controls
# the session_state caching logic. Agno injects session_state automatically
# into any executor function that declares it as a parameter.
# ─────────────────────────────────────────────────────────────────────────

_outbound_calling_workflow = Workflow(
    name="Outbound Calling Workflow",
    description=(
        "Multi-step workflow for outbound calling campaigns: "
        "read leads (with session_state cache), submit batch calls, log results."
    ),
    steps=[
        Step(
            name="Step 1: Read Leads",
            executor=step1_read_leads,
            description=(
                "Read and filter leads from Google Sheet. "
                "Uses session_state cache — sheet is read at most once per session."
            ),
        ),
        Step(
            name="Step 2: Submit Batch Call",
            executor=step2_submit_batch_call,
            description="Submit batch call to ElevenLabs with the filtered leads from Step 1.",
        ),
        Step(
            name="Step 3: Log Results",
            executor=step3_log_results,
            description="Update Google Sheet with call outcomes from Step 2.",
        ),
    ],
    db=db,
)


# ─────────────────────────────────────────────────────────────────────────
# WorkflowTools: Equip workflow as tool to agent
# ─────────────────────────────────────────────────────────────────────────

workflow_tools = WorkflowTools(
    workflow=_outbound_calling_workflow,
    enable_run_workflow=True,  # Enable workflow execution
    enable_think=False,        # Don't need internal thinking scratchpad
    enable_analyze=False,      # Don't need result analysis (agent handles this)
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
        "## READING THE SHEET",
        "When the user provides the Google Sheet URL, read it immediately using the read_sheet tool.",
        "Show the user a summary table of leads found (phone_number + all columns).",
        "Then ask which DYNAMIC_FIELDS to use for the call.",
        "",
        "## RUNNING THE CAMPAIGN",
        "Once you have read the sheet, confirmed DYNAMIC_FIELDS, and the user says go:",
        "1. Filter the leads: keep only rows where status is empty or 'not_contacted'",
        "2. For each lead, keep ONLY: phone_number + the DYNAMIC_FIELDS the user chose (e.g. restaurant_name)",
        "   - Also keep 'language' if present in the sheet",
        "   - Drop all other columns (email, website, status, city, country unless user asked for them)",
        "3. Format the filtered leads as compact JSON (single line, no line breaks inside the array)",
        "4. Trigger the workflow with these four things (plain text, one per line):",
        "  Sheet: https://docs.google.com/spreadsheets/d/YOUR_ID/edit",
        "  DYNAMIC_FIELDS: restaurant_name",
        "  Campaign: Bangkok Restaurants Feb 2026",
        "  LEADS: [{\"phone_number\":\"+66620230022\",\"restaurant_name\":\"Pad Thai Padel\"},{\"phone_number\":\"+66821077730\",\"restaurant_name\":\"Alba Cookies\"}]",
        "IMPORTANT — LEADS line rules:",
        "  - The LEADS value MUST be a single line of compact JSON (no line breaks, no trailing text)",
        "  - Only include phone_number + DYNAMIC_FIELDS (+ language if present in the sheet)",
        "  - This lets the workflow skip the sheet re-read (OAuth not available inside workflow steps)",
        "The workflow will:",
        "   - Use your pre-read leads directly (Step 1)",
        "   - Submit batch calls to ElevenLabs (Step 2)",
        "   - Update results in the sheet (Step 3)",
        "Keep the user informed of progress at each step.",
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
        "DO NOT REMEMBER: restaurant names, phone numbers, or lead details — that data lives in the sheet.",
        "When starting a new session, check if you have a stored sheet URL and ask the user if they want to use the same sheet.",
        "",
        "## COMMUNICATION STYLE",
        "- Be conversational and friendly",
        "- Use emojis for visual progress: 📊 📞 ✓ ⚠️",
        "- Report progress at each major step",
        "- Celebrate success: 'Campaign complete! 🎉'",
        "- Be helpful and professional",
    ],
    tools=[workflow_tools],       # Workflow equipped as tool via WorkflowTools
    pre_hooks=[make_tool_hook("google_sheets")],  # Only Google Sheets needed
    db=db,
    update_memory_on_run=False,   # Disable auto-summaries that pollute cross-session memory
    enable_agentic_memory=True,   # Use agentic memory for deliberate cross-session recall
    add_history_to_context=True,  # Main agent needs context for conversation
    num_history_messages=3,       # Reduced: campaign results are large, high values cause overflow
    add_datetime_to_context=True,
    markdown=True,
)
