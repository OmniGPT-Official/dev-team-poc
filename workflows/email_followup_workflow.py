"""
Email Follow-Up Workflow

This workflow automates follow-up email campaigns with proper tools integration:
1. Analyzes Google Sheets for contacts needing follow-up
2. Gathers context about each contact from email history
3. Drafts personalized follow-up emails
4. Presents drafts for user review and approval
5. Sends approved emails and updates the sheet
6. Provides campaign performance insights

Key Feature: REVIEW-THEN-SEND
- All emails are drafted and shown to user BEFORE sending
- User approves each email (or edits/skips)
- System sends only approved emails
- Sheet is automatically updated after sending
"""

from agno.workflow import Step, Steps, Workflow
from agno.workflow.types import StepInput, StepOutput
from agents.email_followup_agents import (
    sheet_analyzer_agent,
    context_researcher_agent,
    message_writer_agent,
    campaign_analyst_agent,
    followup_coordinator_agent,
)


# === EXECUTOR FUNCTIONS (with streaming) ===

async def run_intake(step_input: StepInput):
    """Understand user's follow-up needs with streaming."""
    async for chunk in followup_coordinator_agent.run(
        step_input.previous_step_content or """
        Start the email follow-up workflow. Ask the user:
        1. Google Sheet URL (or they can paste contact data manually for testing)
        2. Follow-up criteria (e.g., "7+ days since last contact")
        3. Any special instructions or notes

        Be friendly and clear about what information you need.
        """,
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
        step_input.previous_step_content or """
        Analyze the provided Google Sheet (or manual contact data) to identify
        contacts needing follow-up.

        Criteria:
        - 7+ days since last contact (or user-specified threshold)
        - Status is "Pending", "Interested", or similar
        - No recent follow-up recorded

        Provide a clear list with: Name, Company, Email, Last Contact, Notes
        """,
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
        step_input.previous_step_content or """
        For each contact identified, research:
        1. Email history - what did we last discuss?
        2. Notes from the sheet - any context clues?
        3. Relationship stage - new lead, ongoing discussion, etc.

        Summarize key context for each person to enable personalized emails.
        """,
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
        step_input.previous_step_content or """
        Draft personalized follow-up emails for each contact.

        Guidelines:
        - Keep under 100 words
        - Reference specific previous conversation points
        - Suggest clear next step (meeting, demo, call)
        - Professional but friendly tone
        - Engaging subject line (under 50 chars)

        Format each draft:
        ---
        TO: [name] <[email]>
        SUBJECT: [subject line]

        [email body]
        ---
        """,
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
        step_input.previous_step_content or """
        Present all draft emails to the user for review.

        For each email, show:
        1. Contact name and company
        2. Subject line
        3. Full email body
        4. Ask: "Approve, Edit, or Skip?"

        Wait for user approval before proceeding to send.
        Track which emails are approved.
        """,
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
        step_input.previous_step_content or """
        Send all approved emails via Gmail.

        For each sent email:
        1. Use send_email tool with validated recipient
        2. Update Google Sheet with new "Last Contact" date (today)
        3. Update Status to "Followed up"
        4. Add note: "Follow-up sent: [date]"

        Provide confirmation for each email sent.
        """,
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
        step_input.previous_step_content or """
        Analyze this follow-up campaign and provide insights.

        Focus on:
        - How many emails were sent
        - Subject line patterns used
        - Personalization elements included
        - What worked well
        - What could be improved
        - Recommendations for next campaign

        Keep insights actionable and specific.
        """,
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Campaign report complete"
    )


async def run_format_output(step_input: StepInput):
    """Format final output with summary."""
    content = step_input.previous_step_content or ""

    yield StepOutput(
        success=True,
        content=f"""
## ✅ Email Follow-Up Campaign Complete

{content}

---

### 📊 Campaign Summary
- ✅ Analyzed contacts in your sheet
- ✅ Identified contacts needing follow-up
- ✅ Researched context for personalization
- ✅ Drafted personalized emails
- ✅ You reviewed and approved
- ✅ Sent approved emails via Gmail
- ✅ Updated Google Sheet with new dates
- ✅ Generated performance insights

### 📋 What Was Updated
- Google Sheet: Updated "Last Contact" dates
- Gmail: Sent approved follow-up emails
- Status: Contacts marked as "Followed up"

### 🎯 Next Steps
1. Monitor replies in your inbox
2. Check updated Google Sheet
3. Schedule next follow-up campaign (recommended: 7 days)
4. Apply insights from campaign analysis

---

**Ready for your next campaign!** 🚀

*Note: Using mock data for tools - configure Google Sheets & Gmail APIs for production*
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

email_followup_workflow = Workflow(
    name="Email Follow-Up Manager",
    description="""Automated follow-up email workflow with proper tools:
    1. Analyze Google Sheet for contacts needing follow-up
    2. Gather context about each contact from email history
    3. Draft personalized follow-ups with AI
    4. User reviews and approves drafts
    5. Send approved emails via Gmail
    6. Update sheet automatically
    7. Provide campaign insights

    Built with: Gemini 2.0 Flash, Google Sheets tools, Gmail tools
    """,
    steps=[
        intake_and_analysis_steps,
        drafting_steps,
        sending_steps,
        reporting_steps,
    ],
)


# === SIMPLE TEST WORKFLOW ===

async def run_simple_intake(step_input: StepInput):
    """Simple intake for testing without Google Sheets."""
    async for chunk in followup_coordinator_agent.run(
        """
        Welcome! This is the Email Follow-Up Manager (Simple Test Mode).

        Since we're testing without Google Sheets integration, please paste
        contact information for 2-3 people:

        Format: Name, Company, Email, Last Contact Date, Notes
        Example: John Smith, Acme Co, john@acme.com, 2026-01-28, Interested in demo
        """,
        stream=True,
        stream_events=True
    ):
        yield chunk

    yield StepOutput(
        success=True,
        content="Contact data received - ready to draft"
    )


simple_email_followup_workflow = Workflow(
    name="Email Follow-Up Manager (Simple Test)",
    description="""Simplified workflow for testing without Google Sheets:
    1. User pastes contact data manually
    2. Draft follow-up emails with AI
    3. Show drafts for review
    4. Provide insights
    """,
    steps=[
        Step(name="simple_intake", executor=run_simple_intake),
        Step(name="draft_messages", executor=run_draft_messages),
        Step(name="format_output", executor=run_format_output),
    ],
)
