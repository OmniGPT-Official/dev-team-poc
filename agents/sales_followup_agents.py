"""
Sales Follow-Up Manager Agent Configurations

Using Gemini for cost-effective testing.
Switch to Claude for production if needed.
"""

import os
import sys
from agno.agent import Agent
from agno.models.google import Gemini

from db import db
from agno.tools.mcp import MCPTools
from instructions.sales_followup_instructions import (
    SHEET_ANALYZER_INSTRUCTIONS,
    CONTEXT_RESEARCHER_INSTRUCTIONS,
    MESSAGE_WRITER_INSTRUCTIONS,
    CAMPAIGN_ANALYST_INSTRUCTIONS,
    FOLLOWUP_COORDINATOR_INSTRUCTIONS,
)


# Validate Google OAuth credentials
client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")

if not all([client_id, client_secret, refresh_token]):
    print("=" * 80, file=sys.stderr)
    print("⚠️  WARNING: Google OAuth credentials not configured!", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("", file=sys.stderr)
    print("The Follow-Up Manager needs Gmail and Google Sheets access.", file=sys.stderr)
    print("", file=sys.stderr)
    print("To set up:", file=sys.stderr)
    print("1. Run: python3 get_google_token.py", file=sys.stderr)
    print("2. Follow the instructions to get your OAuth credentials", file=sys.stderr)
    print("3. Add the credentials to your .env file", file=sys.stderr)
    print("4. Restart the application", file=sys.stderr)
    print("", file=sys.stderr)
    print("See GOOGLE_MCP_SETUP.md for detailed instructions.", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

# Create Google MCP tool (Gmail + Google Sheets)
google_mcp = MCPTools(
    command="npx -y @pegasusheavy/google-mcp",
    env={
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_CLIENT_SECRET": client_secret,
        "GOOGLE_REFRESH_TOKEN": refresh_token,
    },
    timeout_seconds=60,
)


# Sheet Analyzer - identifies who needs follow-up
sheet_analyzer_agent = Agent(
    name="Sheet Analyzer",
    role="Analyzes Google Sheets to identify contacts needing follow-up",
    model=Gemini(id="gemini-3-flash-preview"),
    db=db,
    add_history_to_context=True,
    markdown=True,
    instructions=SHEET_ANALYZER_INSTRUCTIONS,
    tools=[google_mcp] if all([client_id, client_secret, refresh_token]) else [],
)


# Context Researcher - gathers context for each contact
context_researcher_agent = Agent(
    name="Context Researcher",
    role="Gathers context about each contact from email history and notes",
    model=Gemini(id="gemini-3-flash-preview"),
    db=db,
    add_history_to_context=True,
    markdown=True,
    instructions=CONTEXT_RESEARCHER_INSTRUCTIONS,
    tools=[google_mcp] if all([client_id, client_secret, refresh_token]) else [],
)


# Message Writer - drafts personalized follow-ups
message_writer_agent = Agent(
    name="Message Writer",
    role="Drafts personalized follow-up emails based on context",
    model=Gemini(id="gemini-3-flash-preview"),
    db=db,
    add_history_to_context=True,
    markdown=True,
    instructions=MESSAGE_WRITER_INSTRUCTIONS,
)


# Campaign Analyst - provides insights on campaign performance
campaign_analyst_agent = Agent(
    name="Campaign Analyst",
    role="Analyzes campaign performance and provides actionable insights",
    model=Gemini(id="gemini-3-flash-preview"),
    db=db,
    add_history_to_context=True,
    markdown=True,
    instructions=CAMPAIGN_ANALYST_INSTRUCTIONS,
)


# Follow-Up Coordinator - orchestrates the entire workflow
followup_coordinator_agent = Agent(
    name="Follow-Up Manager",
    role="Coordinates the entire follow-up workflow from sheet analysis to sending emails",
    model=Gemini(id="gemini-3-flash-preview"),
    db=db,
    add_history_to_context=True,
    markdown=True,
    instructions=FOLLOWUP_COORDINATOR_INSTRUCTIONS,
    tools=[google_mcp] if all([client_id, client_secret, refresh_token]) else [],
)
