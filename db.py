"""Supabase PostgreSQL Database Configuration

Shared database setup for all agents, teams, and workflows.
Uses the same pattern as agent_os/main.py.

Environment Variable Priority:
1. DATABASE_URL - Railway/Vercel/Heroku standard (highest priority)
2. SUPABASE_DB_URL - Explicit Supabase connection string
3. SUPABASE_PROJECT + SUPABASE_PASSWORD - Construct connection string
"""

from os import getenv

from agno.db.postgres import PostgresDb
from sqlalchemy import create_engine

# Priority 1: Check for Railway/Vercel/Heroku standard DATABASE_URL
DATABASE_URL = getenv("DATABASE_URL")

# Priority 2: Check for explicit SUPABASE_DB_URL
if not DATABASE_URL:
    DATABASE_URL = getenv("SUPABASE_DB_URL")

# Priority 3: Construct from SUPABASE_PROJECT + SUPABASE_PASSWORD
if not DATABASE_URL:
    SUPABASE_PROJECT = getenv("SUPABASE_PROJECT")
    SUPABASE_PASSWORD = getenv("SUPABASE_PASSWORD")
    if SUPABASE_PROJECT and SUPABASE_PASSWORD:
        DATABASE_URL = f"postgresql://postgres:{SUPABASE_PASSWORD}@db.{SUPABASE_PROJECT}:5432/postgres"

# Create a shared SQLAlchemy engine with a small connection pool.
# pool_size=3 + max_overflow=2 = max 5 simultaneous connections from this app,
# which stays well within Supabase's session-mode pool limit.
# pool_pre_ping rechecks connections that may have gone stale.
_engine = create_engine(
    DATABASE_URL,
    pool_size=3,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Setup PostgreSQL database
db = PostgresDb(db_engine=_engine)

# Export SUPABASE_DB_URL for backward compatibility with knowledge_base.py
SUPABASE_DB_URL = DATABASE_URL
