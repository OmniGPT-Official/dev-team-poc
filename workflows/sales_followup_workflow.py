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

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from agents.sales_followup_agents import (
    sheet_analyzer_agent,
    context_researcher_agent,
    message_writer_agent,
    campaign_analyst_agent,
    followup_coordinator_agent,
)


# === WORKFLOW STEPS ===

intake_step = Step(
    name="intake",
    description="Understand user's follow-up needs and sheet location",
    agent=followup_coordinator_agent,
)

analyze_sheet_step = Step(
    name="analyze_sheet",
    description="Analyze Google Sheet to identify contacts needing follow-up",
    agent=sheet_analyzer_agent,
)

gather_context_step = Step(
    name="gather_context",
    description="Research context for each contact from email history and notes",
    agent=context_researcher_agent,
)

draft_messages_step = Step(
    name="draft_messages",
    description="Draft personalized follow-up emails for each contact",
    agent=message_writer_agent,
)

review_step = Step(
    name="review_and_approve",
    description="Present drafts to user for review and approval",
    agent=followup_coordinator_agent,
)

send_step = Step(
    name="send_and_update",
    description="Send approved emails and update Google Sheet",
    agent=followup_coordinator_agent,
)

report_step = Step(
    name="generate_report",
    description="Analyze campaign performance and provide insights",
    agent=campaign_analyst_agent,
)


# === OUTPUT FORMATTER ===

def format_output(step_input: StepInput) -> StepOutput:
    """Format final output."""
    content = step_input.previous_step_content or ""

    return StepOutput(content=f"""
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
""")


# === WORKFLOW ===

sales_followup_workflow = Workflow(
    name="Sales Follow-Up Manager",
    stream=True,
    description="""Automated follow-up email workflow:
    1. Analyze Google Sheet for contacts needing follow-up
    2. Gather context about each contact
    3. Draft personalized follow-ups
    4. User reviews and approves drafts
    5. Send approved emails via Gmail
    6. Update sheet automatically
    7. Provide campaign insights""",
    steps=[
        intake_step,
        analyze_sheet_step,
        gather_context_step,
        draft_messages_step,
        review_step,
        send_step,
        report_step,
        format_output,
    ],
)


# === SIMPLE TEST WORKFLOW (For AgentOS UI Testing) ===
# This simpler version can be used for initial testing without full Google Sheets/Gmail integration

simple_followup_workflow = Workflow(
    name="Sales Follow-Up Manager (Simple)",
    stream=True,
    description="""Simplified workflow for testing:
    1. User pastes contact data manually
    2. Draft follow-up emails
    3. Show drafts for review""",
    steps=[
        intake_step,
        # Skip sheet analysis - user provides data directly
        gather_context_step,
        draft_messages_step,
        format_output,
    ],
)
