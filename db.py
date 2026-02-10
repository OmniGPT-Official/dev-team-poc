"""Supabase PostgreSQL Database Configuration

Shared database setup for all agents, teams, and workflows.
Uses the same pattern as agent_os/main.py.
"""

from os import getenv

from agno.db.postgres import PostgresDb

# Get database URL from environment
# Try multiple env var names for compatibility:
# 1. DATABASE_URL (standard convention, used by Railway/Vercel/Heroku)
# 2. SUPABASE_DB_URL (legacy, for backwards compatibility)
# 3. Construct from SUPABASE_PROJECT + SUPABASE_PASSWORD (fallback)
db_url = getenv("DATABASE_URL") or getenv("SUPABASE_DB_URL")

if not db_url:
    # Fallback: construct from individual credentials
    SUPABASE_PROJECT = getenv("SUPABASE_PROJECT")
    SUPABASE_PASSWORD = getenv("SUPABASE_PASSWORD")

    if SUPABASE_PROJECT and SUPABASE_PASSWORD:
        db_url = f"postgresql://postgres:{SUPABASE_PASSWORD}@db.{SUPABASE_PROJECT}.supabase.co:5432/postgres"
    else:
        raise ValueError(
            "Database configuration missing. Set one of:\n"
            "  - DATABASE_URL (recommended)\n"
            "  - SUPABASE_DB_URL\n"
            "  - Both SUPABASE_PROJECT and SUPABASE_PASSWORD"
        )

# Setup Supabase PostgreSQL database
db = PostgresDb(db_url=db_url)
