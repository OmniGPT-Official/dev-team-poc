"""Supabase Manager Agent - Manages a user's Supabase project via MCP tools."""

from agno.agent import Agent
from agno.models.google import Gemini

from services.tool_injector import make_tool_hook

from db import db


supabase_manager_agent = Agent(
    name="Supabase Manager",
    model=Gemini(id="gemini-3-flash-preview"),
    description="Manages a user's Supabase project — list tables, run queries, apply migrations, manage edge functions, and check security advisors.",
    instructions=[
        "You are a Supabase Manager that helps users manage their Supabase project using MCP tools.",
        "",
        "## Capabilities",
        "- List and inspect database tables and schemas",
        "- Execute SQL queries (SELECT, INSERT, UPDATE)",
        "- Apply database migrations (CREATE TABLE, ALTER TABLE, etc.)",
        "- List, view, and deploy Edge Functions",
        "- Check security and performance advisors",
        "- Generate TypeScript types from the database schema",
        "",
        "## Safety Rules",
        "- ALWAYS ask for user confirmation before destructive operations (DROP, DELETE, TRUNCATE)",
        "- ALWAYS ask for confirmation before applying migrations that alter or remove columns",
        "- Show the SQL you plan to execute and wait for approval before running it",
        "- Use apply_migration for DDL operations, execute_sql for DML queries",
        "",
        "## Missing Credentials",
        "If Supabase tools are not available, inform the user:",
        "'Please connect your Supabase account in Settings by adding your Personal Access Token and project reference.'",
    ],
    pre_hooks=[make_tool_hook("supabase_mcp")],
    db=db,
    update_memory_on_run=False,
    add_history_to_context=True,
    add_datetime_to_context=True,
    add_name_to_context=True,
    markdown=True,
    reasoning=False,
)
