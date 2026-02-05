"""
Sales Follow-Up Workflow Agents

Using Gemini for cost-effective testing.
"""

import os
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

# Google MCP tool - Gmail and Google Sheets via MCP server
# Only create if credentials are present (Google MCP crashes with empty creds unlike supabase_mcp)
_client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", os.environ.get("GOOGLE_CLIENT_ID", ""))
_client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", os.environ.get("GOOGLE_CLIENT_SECRET", ""))
_refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")

if all([_client_id, _client_secret, _refresh_token]):
    google_mcp = MCPTools(
        command="npx -y @pegasusheavy/google-mcp",
        env={
            "GOOGLE_CLIENT_ID": _client_id,
            "GOOGLE_CLIENT_SECRET": _client_secret,
            "GOOGLE_REFRESH_TOKEN": _refresh_token,
        },
        timeout_seconds=60,
    )
else:
    google_mcp = None


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

message_writer_agent = Agent(
    name="Message Writer",
    role="Drafts personalized follow-up emails based on context",
    model=Gemini(id="gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=MESSAGE_WRITER_INSTRUCTIONS,
    tool_call_limit=10,
)

campaign_analyst_agent = Agent(
    name="Campaign Analyst",
    role="Analyzes campaign performance and provides actionable insights",
    model=Gemini(id="gemini-3-flash-preview"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=CAMPAIGN_ANALYST_INSTRUCTIONS,
    tool_call_limit=10,
)

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
