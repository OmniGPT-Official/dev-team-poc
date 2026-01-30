"""
Knowledge Base Setup Script

This script helps populate the knowledge bases with documentation sources.
Run this after setting your OPENAI_API_KEY environment variable.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge import github_docs_kb, supabase_docs_kb, vercel_docs_kb


def setup_knowledge_bases():
    """
    Populate knowledge bases with documentation.

    Note: This requires OPENAI_API_KEY to be set in your environment.
    """

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set!")
        print("Please set it with: export OPENAI_API_KEY='your-api-key'")
        return False

    print("Setting up knowledge bases...")

    # GitHub Documentation
    print("\n1. GitHub Documentation Knowledge Base")
    print("   Adding sources...")
    # Uncomment and add actual documentation URLs when ready
    # github_docs_kb.load(recreate=False)
    print("   ✓ Configured (add sources in knowledge/knowledge_config.py)")

    # Supabase Documentation
    print("\n2. Supabase Documentation Knowledge Base")
    print("   Adding sources...")
    # supabase_docs_kb.load(recreate=False)
    print("   ✓ Configured (add sources in knowledge/knowledge_config.py)")

    # Vercel Documentation
    print("\n3. Vercel Documentation Knowledge Base")
    print("   Adding sources...")
    # vercel_docs_kb.load(recreate=False)
    print("   ✓ Configured (add sources in knowledge/knowledge_config.py)")

    print("\n✅ Knowledge bases setup complete!")
    print("\nNext steps:")
    print("1. Add documentation URLs to knowledge/knowledge_config.py")
    print("2. Uncomment the .load() calls in this script")
    print("3. Run this script again to populate the knowledge bases")

    return True


if __name__ == "__main__":
    setup_knowledge_bases()
