"""
Sales Follow-Up Workflow Agents

Architecture: WORKFLOW (not Team)
- These are standalone agents used in a sequential workflow
- The "coordinator" is NOT a team manager - it's just called at different workflow steps
- For Team architecture example, see: teams/product_team.py

Using Gemini for cost-effective testing.
Switch to Claude for production if needed.
"""

import os
import sys
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.google import Gemini
from agno.tools.mcp import MCPTools
from instructions.sales_followup_instructions import (
    SHEET_ANALYZER_INSTRUCTIONS,
    CONTEXT_RESEARCHER_INSTRUCTIONS,
    MESSAGE_WRITER_INSTRUCTIONS,
    CAMPAIGN_ANALYST_INSTRUCTIONS,
    FOLLOWUP_COORDINATOR_INSTRUCTIONS,
)


# Get Google OAuth credentials
# Support both naming conventions: GOOGLE_OAUTH_* (preferred) and GOOGLE_* (fallback)
client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or os.environ.get("GOOGLE_CLIENT_ID", "")
client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or os.environ.get("GOOGLE_CLIENT_SECRET", "")
refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")

# Warn if credentials are missing (but still create the tool)
if not all([client_id, client_secret, refresh_token]):
    print("=" * 80, file=sys.stderr)
    print("⚠️  WARNING: Google OAuth credentials not fully configured!", file=sys.stderr)
    print("=" * 80, file=sys.stderr)
    print("", file=sys.stderr)
    print("The Sales Follow-Up Workflow needs Gmail and Google Sheets access.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Missing credentials:", file=sys.stderr)
    if not client_id:
        print("  ❌ GOOGLE_OAUTH_CLIENT_ID or GOOGLE_CLIENT_ID", file=sys.stderr)
    if not client_secret:
        print("  ❌ GOOGLE_OAUTH_CLIENT_SECRET or GOOGLE_CLIENT_SECRET", file=sys.stderr)
    if not refresh_token:
        print("  ❌ GOOGLE_OAUTH_REFRESH_TOKEN", file=sys.stderr)
    print("", file=sys.stderr)
    print("To set up OAuth credentials in your cloud environment:", file=sys.stderr)
    print("1. Set these environment variables in your deployment platform:", file=sys.stderr)
    print("   GOOGLE_OAUTH_CLIENT_ID=your-client-id", file=sys.stderr)
    print("   GOOGLE_OAUTH_CLIENT_SECRET=your-secret", file=sys.stderr)
    print("   GOOGLE_OAUTH_REFRESH_TOKEN=your-refresh-token", file=sys.stderr)
    print("2. Restart your application", file=sys.stderr)
    print("", file=sys.stderr)
    print("For now, the 'Test Mode' workflow will work without credentials.", file=sys.stderr)
    print("=" * 80, file=sys.stderr)

# Create Google MCP tool (Gmail + Google Sheets)
# This MCP server provides: gmail_send_email, gmail_search, sheets_read, sheets_write
# Only create if ALL credentials are present (Google MCP crashes with empty creds)
if all([client_id, client_secret, refresh_token]):
    google_mcp = MCPTools(
        command="npx -y @pegasusheavy/google-mcp",
        env={
            "GOOGLE_CLIENT_ID": client_id,
            "GOOGLE_CLIENT_SECRET": client_secret,
            "GOOGLE_REFRESH_TOKEN": refresh_token,
        },
        timeout_seconds=60,
    )
    print("✅ Google MCP tools initialized successfully", file=sys.stderr)
else:
    google_mcp = None
    print("⚠️  Google MCP tools NOT initialized (credentials missing)", file=sys.stderr)


# Sheet Analyzer - identifies who needs follow-up
sheet_analyzer_agent = Agent(
    name="Sheet Analyzer",
    role="Analyzes Google Sheets to identify contacts needing follow-up",
    model=Gemini(id="gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=SHEET_ANALYZER_INSTRUCTIONS,
    tools=[google_mcp] if google_mcp else [],
    tool_call_limit=50,
)


# Context Researcher - gathers context for each contact
context_researcher_agent = Agent(
    name="Context Researcher",
    role="Gathers context about each contact from email history and notes",
    model=Gemini(id="gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=CONTEXT_RESEARCHER_INSTRUCTIONS,
    tools=[google_mcp] if google_mcp else [],
    tool_call_limit=50,
)


# Message Writer - drafts personalized follow-ups (no tools needed - writing only)
message_writer_agent = Agent(
    name="Message Writer",
    role="Drafts personalized follow-up emails based on context",
    model=Gemini(id="gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=MESSAGE_WRITER_INSTRUCTIONS,
    tool_call_limit=10,  # Low limit - this agent only writes, doesn't use tools
)


# Campaign Analyst - provides insights on campaign performance (no tools - analysis only)
campaign_analyst_agent = Agent(
    name="Campaign Analyst",
    role="Analyzes campaign performance and provides actionable insights",
    model=Gemini(id="gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=CAMPAIGN_ANALYST_INSTRUCTIONS,
    tool_call_limit=10,  # Low limit - this agent analyzes, doesn't use external tools
)


# Follow-Up Coordinator - orchestrates workflow steps
# NOTE: This is NOT a team manager - it's just called at different workflow steps
# For actual team architecture, see: teams/product_team.py
followup_coordinator_agent = Agent(
    name="Follow-Up Workflow Coordinator",
    role="Handles user interaction and workflow orchestration at different stages",
    model=Gemini(id="gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=FOLLOWUP_COORDINATOR_INSTRUCTIONS,
    tools=[google_mcp] if google_mcp else [],
    tool_call_limit=100,
)
