"""
Sales Follow-Up Manager Workflow

This workflow automates follow-up email campaigns by:
1. Analyzing Google Sheets for contacts needing follow-up
2. Gathering context about each contact
3. Drafting personalized follow-up emails
4. Presenting drafts for user review and approval
5. Sending approved emails and updating the sheet
6. Providing campaign performance insights

Key Feature: REVIEW-THEN-SEND
- All emails are drafted and shown to user BEFORE sending
- User approves each email (or edits/skips)
- System sends only approved emails
- Sheet is automatically updated after sending
"""

import asyncio
from agno.agent import Agent
from agno.workflow import Step, Steps, Workflow
from agno.workflow.types import StepInput, StepOutput
from agents.sales_followup_agents import (
    sheet_analyzer_agent,
    context_researcher_agent,
    message_writer_agent,
    campaign_analyst_agent,
    followup_coordinator_agent,
)


def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# === EXECUTOR FUNCTIONS (with streaming) ===

async def run_intake(step_input: StepInput):
    """Understand user's follow-up needs with streaming."""
    async for chunk in followup_coordinator_agent.run(
        step_input.previous_step_content or "Start the follow-up workflow. Ask user about their Google Sheet location and what they want to accomplish.",
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Intake complete - ready to analyze contacts"
    )


async def run_analyze_sheet(step_input: StepInput):
    """Analyze Google Sheet to identify contacts with streaming."""
    async for chunk in sheet_analyzer_agent.run(
        step_input.previous_step_content or "Analyze the Google Sheet to identify contacts needing follow-up (7+ days since last contact).",
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Sheet analysis complete - contacts identified"
    )


async def run_gather_context(step_input: StepInput):
    """Gather context for each contact with streaming."""
    async for chunk in context_researcher_agent.run(
        step_input.previous_step_content or "Research email history and notes for each contact to gather context for personalization.",
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Context research complete - ready to draft"
    )


async def run_draft_messages(step_input: StepInput):
    """Draft personalized follow-up emails with streaming."""
    async for chunk in message_writer_agent.run(
        step_input.previous_step_content or "Draft personalized follow-up emails for each contact based on the context gathered.",
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Draft emails complete - ready for review"
    )


async def run_review(step_input: StepInput):
    """Present drafts for user review with streaming."""
    async for chunk in followup_coordinator_agent.run(
        step_input.previous_step_content or "Present all draft emails to the user for review and approval. Show each email clearly with contact name, subject line, and message body.",
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Review complete - emails approved"
    )


async def run_send(step_input: StepInput):
    """Send approved emails and update sheet with streaming."""
    async for chunk in followup_coordinator_agent.run(
        step_input.previous_step_content or "Send all approved emails via Gmail and update the Google Sheet with new 'last contact date' for each contact.",
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Emails sent and sheet updated"
    )


async def run_report(step_input: StepInput):
    """Generate campaign performance report with streaming."""
    async for chunk in campaign_analyst_agent.run(
        step_input.previous_step_content or "Analyze the campaign performance and provide insights about what worked and what didn't.",
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Campaign report complete"
    )


def run_format_output(step_input: StepInput) -> StepOutput:
    """Format final output with summary."""
    content = step_input.previous_step_content or ""

    return StepOutput(
        success=True,
        content=f"""
## Follow-Up Campaign Complete

{content}

---

### What Happened
1. ✅ Analyzed your Google Sheet
2. ✅ Identified contacts needing follow-up
3. ✅ Researched context for personalization
4. ✅ Drafted follow-up emails
5. ✅ You reviewed and approved
6. ✅ Sent approved emails
7. ✅ Updated Google Sheet with new status
8. ✅ Generated campaign insights

### Next Steps
- Your Google Sheet has been updated with today's follow-ups
- Contacts who received emails have new "last contact date"
- Check your sent folder to see the emails
- Come back next week to follow up with new contacts

*Ready for your next campaign whenever you are!*
"""
    )


# === GROUPED STEPS ===

intake_and_analysis_steps = Steps(
    name="Intake & Analysis",
    steps=[
        Step(name="intake", executor=run_intake),
        Step(name="analyze_sheet", executor=run_analyze_sheet),
    ],
)

drafting_steps = Steps(
    name="Context & Drafting",
    steps=[
        Step(name="gather_context", executor=run_gather_context),
        Step(name="draft_messages", executor=run_draft_messages),
    ],
)

sending_steps = Steps(
    name="Review & Send",
    steps=[
        Step(name="review_and_approve", executor=run_review),
        Step(name="send_and_update", executor=run_send),
    ],
)

reporting_steps = Steps(
    name="Reporting",
    steps=[
        Step(name="generate_report", executor=run_report),
        Step(name="format_output", executor=run_format_output),
    ],
)


# === MAIN WORKFLOW ===

sales_followup_workflow = Workflow(
    name="Sales Follow-Up Workflow",
    description="""Automated follow-up email workflow (requires Google OAuth):
    1. Analyze Google Sheet for contacts needing follow-up
    2. Gather context about each contact from Gmail
    3. Draft personalized follow-ups
    4. User reviews and approves drafts
    5. Send approved emails via Gmail
    6. Update sheet automatically
    7. Provide campaign insights

    Prerequisites: Google OAuth credentials configured (visit /google-auth)""",
    steps=[
        intake_and_analysis_steps,
        drafting_steps,
        sending_steps,
        reporting_steps,
    ],
)


# === SIMPLE TEST WORKFLOW (For Testing Without Google OAuth) ===

def run_simple_intake(step_input: StepInput) -> StepOutput:
    """Simple intake for testing without Google Sheets - provides mock data."""
    mock_data = """
I'll use this test data for the follow-up workflow:

**CONTACTS_NEEDING_FOLLOWUP: 3**

**Contact 1:**
- Name: Sarah Chen
- Company: TechFlow AI
- Email: sarah@techflow.ai
- Last contact: 2025-01-20
- Days since: 15 days
- Status: Interested
- Notes: Expressed interest in our API integration. Asked for pricing details. Mentioned they're evaluating 3 vendors and decision timeline is end of Q1.

**Contact 2:**
- Name: Marcus Rodriguez
- Company: DataSync Solutions
- Email: marcus@datasync.io
- Last contact: 2025-01-15
- Days since: 20 days
- Status: Demo completed
- Notes: Loved the demo, especially the real-time sync feature. Said they need to get buy-in from CTO. Asked about enterprise pricing and security compliance (SOC 2, GDPR).

**Contact 3:**
- Name: Emily Patel
- Company: CloudScale Inc
- Email: emily@cloudscale.com
- Last contact: 2025-01-10
- Days since: 25 days
- Status: Proposal sent
- Notes: Received our proposal 3 weeks ago. Mentioned they're in budget planning cycle. Last email mentioned they'd have feedback "by mid-January" but no response yet.

Ready to draft personalized follow-up emails for these contacts!
"""

    result = _run_async(followup_coordinator_agent.arun(
        f"""You're running in TEST MODE (no Google OAuth configured).

I'll provide you with mock contact data to test the follow-up workflow.

{mock_data}

Present this data to the user and confirm we're ready to draft follow-up emails.
Explain that this is test mode and in production mode, this data would come from Google Sheets automatically."""
    ))

    return StepOutput(
        success=True,
        content=mock_data
    )


def run_simple_draft(step_input: StepInput) -> StepOutput:
    """Draft messages using the mock data."""
    result = _run_async(message_writer_agent.arun(
        f"""Based on this contact data, draft personalized follow-up emails:

{step_input.previous_step_content}

Draft a follow-up email for each contact. Remember:
- Keep under 100 words
- Reference specific context
- One clear call-to-action
- Natural, conversational tone
- Specific subject lines"""
    ))

    output = result.content or "Draft emails complete"
    return StepOutput(
        success=True,
        content=output
    )


simple_followup_workflow = Workflow(
    name="Sales Follow-Up Workflow (Test Mode)",
    description="""Test workflow without Google OAuth:
    1. Uses mock contact data (no Google Sheets needed)
    2. Drafts personalized follow-up emails
    3. Shows drafts for review

    Perfect for testing when Google OAuth is not configured.""",
    steps=[
        Step(name="simple_intake", executor=run_simple_intake),
        Step(name="draft_messages", executor=run_simple_draft),
        Step(name="format_output", executor=run_format_output),
    ],
)
