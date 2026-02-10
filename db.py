"""Supabase PostgreSQL Database Configuration

Shared database setup for all agents, teams, and workflows.
Uses the same pattern as agent_os/main.py.
"""

from os import getenv

from agno.db.postgres import PostgresDb

# Get database URL from environment
# Try multiple env var names for Railway/Vercel/Heroku compatibility:
# 1. DATABASE_URL (standard for Railway/Vercel/Heroku)
# 2. SUPABASE_DB_URL (legacy/explicit Supabase)
# 3. Construct from SUPABASE_PROJECT + SUPABASE_PASSWORD (fallback)
db_url = getenv("DATABASE_URL") or getenv("SUPABASE_DB_URL")

if not db_url:
    # Fallback: construct from individual credentials
    SUPABASE_PROJECT = getenv("SUPABASE_PROJECT")
    SUPABASE_PASSWORD = getenv("SUPABASE_PASSWORD")
    if SUPABASE_PROJECT and SUPABASE_PASSWORD:
        db_url = f"postgresql://postgres:{SUPABASE_PASSWORD}@db.{SUPABASE_PROJECT}.supabase.co:5432/postgres"

# Export for backward compatibility (used by knowledge_base.py)
SUPABASE_DB_URL = db_url

# Setup Supabase PostgreSQL database
db = PostgresDb(db_url=db_url)
