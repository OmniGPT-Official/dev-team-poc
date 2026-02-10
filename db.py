"""Supabase PostgreSQL Database Configuration

Shared database setup for all agents, teams, and workflows.
Uses the same pattern as agent_os/main.py.
"""

from os import getenv

from agno.db.postgres import PostgresDb

# Get Supabase credentials from environment
SUPABASE_DB_URL = getenv("SUPABASE_DB_URL")
if not SUPABASE_DB_URL:
    SUPABASE_PROJECT = getenv("SUPABASE_PROJECT")
    SUPABASE_PASSWORD = getenv("SUPABASE_PASSWORD")
    SUPABASE_DB_URL = f"postgresql://postgres:{SUPABASE_PASSWORD}@db.{SUPABASE_PROJECT}:5432/postgres"

# Setup Supabase PostgreSQL database
db = PostgresDb(db_url=SUPABASE_DB_URL)
