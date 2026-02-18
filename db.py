"""Supabase PostgreSQL Database Configuration

Shared database setup for all agents, teams, and workflows.

Set SUPABASE_DB_URL to a transaction-mode pooler connection string
(port 6543 with ?pgbouncer=true) to avoid pool exhaustion on the free plan.
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
