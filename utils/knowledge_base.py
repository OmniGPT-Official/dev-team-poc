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
    """Get or create the singleton knowledge base instance."""
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        contents_db = PostgresDb(
            db_url=SUPABASE_DB_URL,
            knowledge_table="knowledge_contents"
        )
        vector_db = PgVector(
            table_name="knowledge_vectors",
            db_url=SUPABASE_DB_URL
        )
        _knowledge_base_instance = Knowledge(
            vector_db=vector_db,
            contents_db=contents_db,
        )
    return _knowledge_base_instance
