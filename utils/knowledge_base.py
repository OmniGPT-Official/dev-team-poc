"""
Knowledge Base - Agno Knowledge with PostgreSQL and PgVector

Uses Agno's built-in Knowledge system with:
- PostgresDb for content tracking
- PgVector for vector embeddings and semantic search
"""

from agno.knowledge.knowledge import Knowledge
from agno.db.postgres import PostgresDb
from agno.vectordb.pgvector import PgVector

from db import SUPABASE_DB_URL


# =========================================================================
# SINGLETON INSTANCE (lazy-initialized to avoid DB connection at import time)
# =========================================================================

_knowledge_base_instance = None


def get_knowledge_base() -> Knowledge:
    """Get or create the singleton knowledge base instance.

    Uses the 'ai' schema in Supabase for all knowledge base tables.
    Tables are auto-created on first use if they don't exist.
    """
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        contents_db = PostgresDb(
            db_url=SUPABASE_DB_URL,
            db_schema="ai",  # Use "ai" schema
            knowledge_table="knowledge_contents",
            create_schema=True  # Auto-create schema and tables if they don't exist
        )
        vector_db = PgVector(
            table_name="knowledge_vectors",
            schema="ai",  # Use "ai" schema
            db_url=SUPABASE_DB_URL,
            create_schema=True  # Auto-create schema and tables if they don't exist
        )
        _knowledge_base_instance = Knowledge(
            vector_db=vector_db,
            contents_db=contents_db,
        )
    return _knowledge_base_instance
