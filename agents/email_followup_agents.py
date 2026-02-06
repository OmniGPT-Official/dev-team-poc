"""
Email Follow-Up Agents

These agents coordinate the email follow-up workflow with proper tools
and language model configuration.
"""

from agno.agent import Agent
from agno.models.google import Gemini
from tools.google_sheets_tools import (
    read_google_sheet,
    update_sheet_row,
    find_contacts_needing_followup
)
from tools.gmail_tools import (
    search_gmail_history,
    send_email,
    check_email_deliverability
)

# Use Gemini 3 Flash Preview for cost-effective POC testing
# Cost: ~$0.19 per million tokens vs ~$9 for Claude Sonnet 4.5
MODEL = Gemini(id="gemini-3-flash-preview")


# Sheet Analyzer - identifies contacts needing follow-up
sheet_analyzer_agent = Agent(
    name="Sheet Analyzer",
    model=MODEL,
    description="Analyzes Google Sheets to identify contacts needing follow-up",
    instructions=[
        "You analyze Google Sheets containing sales leads and contacts",
        "You identify contacts that need follow-up based on 'Last Contact' date",
        "Default threshold: 7+ days since last contact",
        "You provide a clear list of contacts with their details",
        "Format: Name, Company, Email, Last Contact Date, Status, Notes",
        "Be specific about why each contact needs follow-up"
    ],
    tools=[
        read_google_sheet,
        find_contacts_needing_followup
    ]
)


# Context Researcher - gathers email history and context
context_researcher_agent = Agent(
    name="Context Researcher",
    model=MODEL,
    description="Researches email history and gathers context for personalization",
    instructions=[
        "You research past email conversations with contacts",
        "You extract key context: previous topics, interests, pain points",
        "You identify relevant notes from the Google Sheet",
        "You summarize the relationship history for each contact",
        "Your research enables highly personalized follow-ups",
        "Focus on: last conversation topic, expressed interests, pending actions"
    ],
    tools=[
        search_gmail_history,
        read_google_sheet
    ]
)


# Message Writer - drafts personalized emails
message_writer_agent = Agent(
    name="Message Writer",
    model=MODEL,
    description="Drafts personalized follow-up emails based on context",
    instructions=[
        "You write personalized, engaging follow-up emails",
        "Use context from email history and notes for personalization",
        "Keep emails concise (under 100 words preferred)",
        "Include specific references to previous conversations",
        "Suggest clear next steps (meeting time, demo, call)",
        "Use professional but friendly tone",
        "Subject lines should be specific and engaging (under 50 chars)",
        "Validate email addresses before drafting",
        "Format each draft clearly with: TO, SUBJECT, BODY"
    ],
    tools=[
        check_email_deliverability
    ]
)


# Campaign Analyst - provides insights
campaign_analyst_agent = Agent(
    name="Campaign Analyst",
    model=MODEL,
    description="Analyzes campaign performance and provides insights",
    instructions=[
        "You analyze follow-up campaign performance",
        "You identify patterns: what works, what doesn't",
        "You provide actionable recommendations",
        "Focus on: subject lines, timing, personalization, response rates",
        "Present insights in plain language, not jargon",
        "Use bullet points for clarity",
        "Include specific examples from the data",
        "Suggest concrete improvements for next campaign"
    ],
    tools=[
        read_google_sheet,
        search_gmail_history
    ]
)


# Follow-Up Coordinator - orchestrates the process
followup_coordinator_agent = Agent(
    name="Follow-Up Coordinator",
    model=MODEL,
    description="Coordinates the entire follow-up workflow",
    instructions=[
        "You coordinate the email follow-up process end-to-end",
        "You communicate clearly with the user at each step",
        "CRITICAL: Always show draft emails to user for approval BEFORE sending",
        "You never send emails without explicit user approval",
        "You update Google Sheets after sending emails",
        "You provide clear status updates and next steps",
        "You are helpful, professional, and detail-oriented",
        "When showing drafts, format them clearly for easy review",
        "Track which emails were approved vs skipped"
    ],
    tools=[
        read_google_sheet,
        update_sheet_row,
        send_email,
        search_gmail_history
    ]
)
