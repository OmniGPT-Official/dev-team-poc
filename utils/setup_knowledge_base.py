"""
Setup Knowledge Base Schema

Programmatically creates the 'ai' schema and enables pgvector extension.
This script ensures the knowledge base is properly configured before first use.

Run this once after deploying to a new environment:
    python utils/setup_knowledge_base.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import db module
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from db import SUPABASE_DB_URL


def setup_knowledge_base_schema():
    """
    Create the 'ai' schema and enable pgvector extension.

    This must be run with a database user that has:
    - CREATE SCHEMA privileges
    - CREATE EXTENSION privileges (usually requires superuser)
    """
    print("🔧 Setting up Knowledge Base schema...")

    engine = create_engine(SUPABASE_DB_URL)

    try:
        with engine.connect() as conn:
            # Enable pgvector extension (required for vector operations)
            print("  📦 Enabling pgvector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("  ✅ pgvector extension enabled")

            # Create 'ai' schema if it doesn't exist
            print("  📁 Creating 'ai' schema...")
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS ai;"))
            conn.commit()
            print("  ✅ 'ai' schema created")

            # Verify schema exists
            result = conn.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'ai';")
            )
            if result.fetchone():
                print("  ✅ Verified 'ai' schema exists")
            else:
                print("  ❌ Failed to verify 'ai' schema")
                return False

            # Verify pgvector extension is enabled
            result = conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            )
            if result.fetchone():
                print("  ✅ Verified pgvector extension is enabled")
            else:
                print("  ❌ Failed to verify pgvector extension")
                return False

        print("\n✅ Knowledge Base schema setup complete!")
        print("\nℹ️  Tables will be auto-created on first use:")
        print("   - ai.knowledge_contents (PostgreSQL)")
        print("   - ai.knowledge_vectors (PgVector with HNSW index)")
        return True

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure your database user has CREATE SCHEMA privileges")
        print("2. Ensure your database user has CREATE EXTENSION privileges")
        print("3. For Supabase, pgvector must be enabled in your project settings:")
        print("   Dashboard > Database > Extensions > pgvector")
        return False


if __name__ == "__main__":
    success = setup_knowledge_base_schema()
    sys.exit(0 if success else 1)
