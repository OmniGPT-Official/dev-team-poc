"""
Knowledge Base - Agno Knowledge with PostgreSQL and PgVector

Uses Agno's built-in Knowledge system with:
- PostgresDb for content tracking
- PgVector for vector embeddings and semantic search
"""

import os
from agno.knowledge.knowledge import Knowledge
from agno.db.postgres import PostgresDb
from agno.vectordb.pgvector import PgVector


# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Please set it in your .env file."
    )


# Initialize PostgreSQL database for content tracking
contents_db = PostgresDb(
    db_url=DATABASE_URL,
    knowledge_table="knowledge_contents"
)


# Initialize PgVector for embeddings
vector_db = PgVector(
    table_name="knowledge_vectors",
    db_url=DATABASE_URL
)


# Initialize Agno Knowledge
knowledge = Knowledge(
    vector_db=vector_db,
    contents_db=contents_db,
)


# =========================================================================
# SINGLETON INSTANCE
# =========================================================================

_knowledge_base_instance = None


def get_knowledge_base() -> Knowledge:
    """Get or create the singleton knowledge base instance."""
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        _knowledge_base_instance = knowledge
    return _knowledge_base_instance
