"""
Knowledge Base Configuration

This module defines knowledge bases for documentation and resources.
Uses PostgreSQL with PgVector for vector storage and OpenAI for embeddings.
"""

import os
from agno.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.db.postgres import PostgresDb

# PostgreSQL connection for knowledge bases (vector storage)
KNOWLEDGE_DB_URL = "postgresql+psycopg://postgres.qmfsbntaygggtjzlemyg:87BagtxA0pe2pcqW@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

# Only initialize knowledge bases if OpenAI API key is set
if not os.getenv("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not set. Knowledge bases disabled.")
    ALL_KNOWLEDGE_BASES = []
else:
    # GitHub Documentation Database
    github_contents_db = PostgresDb(
        KNOWLEDGE_DB_URL,
        id="github_docs_db",
        knowledge_table="github_docs_contents",
    )

    # Supabase Documentation Database
    supabase_contents_db = PostgresDb(
        KNOWLEDGE_DB_URL,
        id="supabase_docs_db",
        knowledge_table="supabase_docs_contents",
    )

    # Vercel Documentation Database
    vercel_contents_db = PostgresDb(
        KNOWLEDGE_DB_URL,
        id="vercel_docs_db",
        knowledge_table="vercel_docs_contents",
    )

    # GitHub Documentation Knowledge Base
    github_docs_kb = Knowledge(
        name="GitHub Documentation",
        description="GitHub API and platform documentation",
        vector_db=PgVector(
            db_url=KNOWLEDGE_DB_URL,
            table_name="github_docs_vectors",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        contents_db=github_contents_db,
    )

    # Supabase Documentation Knowledge Base
    supabase_docs_kb = Knowledge(
        name="Supabase Documentation",
        description="Supabase database and API documentation",
        vector_db=PgVector(
            db_url=KNOWLEDGE_DB_URL,
            table_name="supabase_docs_vectors",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        contents_db=supabase_contents_db,
    )

    # Vercel Documentation Knowledge Base
    vercel_docs_kb = Knowledge(
        name="Vercel Documentation",
        description="Vercel deployment and hosting documentation",
        vector_db=PgVector(
            db_url=KNOWLEDGE_DB_URL,
            table_name="vercel_docs_vectors",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        contents_db=vercel_contents_db,
    )

    # All knowledge bases
    ALL_KNOWLEDGE_BASES = [
        github_docs_kb,
        supabase_docs_kb,
        vercel_docs_kb,
    ]
