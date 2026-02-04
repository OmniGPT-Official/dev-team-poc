"""
Sales Follow-Up Manager Agent Configurations

Using Gemini for cost-effective testing.
Switch to Claude for production if needed.
"""

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.google import Gemini
from instructions.sales_followup_instructions import (
    SHEET_ANALYZER_INSTRUCTIONS,
    CONTEXT_RESEARCHER_INSTRUCTIONS,
    MESSAGE_WRITER_INSTRUCTIONS,
    CAMPAIGN_ANALYST_INSTRUCTIONS,
    FOLLOWUP_COORDINATOR_INSTRUCTIONS,
)


# Sheet Analyzer - identifies who needs follow-up
sheet_analyzer_agent = Agent(
    name="Sheet Analyzer",
    role="Analyzes Google Sheets to identify contacts needing follow-up",
    model=Gemini(id="gemini-3-flash"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=SHEET_ANALYZER_INSTRUCTIONS,
    # TODO: Add Google Sheets MCP tool when available
)


# Context Researcher - gathers context for each contact
context_researcher_agent = Agent(
    name="Context Researcher",
    role="Gathers context about each contact from email history and notes",
    model=Gemini(id="gemini-3-flash"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=CONTEXT_RESEARCHER_INSTRUCTIONS,
    # TODO: Add Gmail MCP tool when available
)


# Message Writer - drafts personalized follow-ups
message_writer_agent = Agent(
    name="Message Writer",
    role="Drafts personalized follow-up emails based on context",
    model=Gemini(id="gemini-3-flash"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=MESSAGE_WRITER_INSTRUCTIONS,
)


# Campaign Analyst - provides insights on campaign performance
campaign_analyst_agent = Agent(
    name="Campaign Analyst",
    role="Analyzes campaign performance and provides actionable insights",
    model=Gemini(id="gemini-3-flash"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=CAMPAIGN_ANALYST_INSTRUCTIONS,
)


# Follow-Up Coordinator - orchestrates the entire workflow
followup_coordinator_agent = Agent(
    name="Follow-Up Manager",
    role="Coordinates the entire follow-up workflow from sheet analysis to sending emails",
    model=Gemini(id="gemini-3-flash"),
    db=SqliteDb(db_file="agno.db"),
    add_history_to_context=True,
    markdown=True,
    instructions=FOLLOWUP_COORDINATOR_INSTRUCTIONS,
    # TODO: Add Google Sheets + Gmail MCP tools when available
)
