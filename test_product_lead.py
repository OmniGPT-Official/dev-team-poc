"""
Test Script for Product Lead Agent

This script demonstrates how to use the Product Lead agent
to trigger the complete software development workflow.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.product_lead import product_lead_agent


def main():
    """Test the Product Lead agent with a sample request."""

    print("=" * 80)
    print("🚀 PRODUCT LEAD AGENT - TEST")
    print("=" * 80)
    print()

    # Example 1: Simple feature request
    print("📝 Test Case: Blog Post Scheduling Feature")
    print("-" * 80)

    user_request = """
    Create a blog post scheduling system for content creators.
    They should be able to schedule posts, set publish times, and manage drafts.
    """

    print(f"User Request: {user_request.strip()}")
    print()
    print("Agent Response:")
    print("-" * 80)

    # Run the agent
    product_lead_agent.print_response(user_request, stream=True)

    print()
    print("=" * 80)
    print("✅ Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
