#!/usr/bin/env python3
"""
Pre-Deployment Verification CLI

Quick command to verify your changes are safe to deploy.

Usage:
    python3 scripts/verify_deployment.py

Or make it executable:
    chmod +x scripts/verify_deployment.py
    ./scripts/verify_deployment.py
"""

import sys
from pathlib import Path

# Add project root to path so we can import agents
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.pre_deployment_checker import pre_deployment_agent


def main():
    print("\n🔍 Running Pre-Deployment Verification...\n")
    print("=" * 60)

    try:
        # Run the verification agent
        response = pre_deployment_agent.run(
            "Check all my current changes and verify they are safe to deploy. "
            "Run all verification checks and give me a comprehensive report."
        )

        # Print the response
        print(response.content)

        # Check if deployment is safe
        if "DO NOT DEPLOY" in response.content or "❌ FAIL" in response.content:
            print("\n⚠️  VERIFICATION FAILED - Please fix issues before deploying")
            sys.exit(1)
        elif "SAFE TO DEPLOY" in response.content:
            print("\n✅ Verification passed - Safe to create PR and deploy!")
            sys.exit(0)
        else:
            print("\n⚠️  Could not determine verification status")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error running verification: {e}")
        print("\nPlease check:")
        print("  1. You have OPENAI_API_KEY set in environment")
        print("  2. You're in the project root directory")
        print("  3. All dependencies are installed (pip install agno)")
        sys.exit(1)


if __name__ == "__main__":
    main()
